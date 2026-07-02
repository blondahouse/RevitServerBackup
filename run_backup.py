import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backup_manager.backup_manager import BackupManager, BackupConfig


REQUIRED_CONFIG_KEYS = [
    "source",
    "target",
    "db_location",
    "servername",
    "rstoollocation",
    "temp_folder",
    "root_folder_id",
]

VALID_MODES = ("all", "edited", "selected")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back up one or more Revit Server instances."
    )

    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to a single config JSON file. Default: config.json",
    )
    config_group.add_argument(
        "--config-dir",
        help="Path to a folder with multiple *.json config files.",
    )

    parser.add_argument(
        "-m",
        "--mode",
        choices=VALID_MODES,
        help="Backup mode. If omitted, uses config 'mode' or defaults to 'edited'.",
    )
    parser.add_argument(
        "--model",
        help="Model path for selected mode, e.g. 'Project\\Model.rvt'.",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Folder for log files. Default: logs",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop processing remaining instances after the first configuration/runtime error.",
    )

    return parser.parse_args()


def safe_file_name(value: str) -> str:
    safe = []
    for char in value:
        if char.isalnum() or char in ("-", "_", "."):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("._") or "revit_backup"


def setup_logging(log_dir: Path, instance_name: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{safe_file_name(instance_name)}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    return log_path


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def load_config_file(path: Path) -> List[Tuple[Path, str, Dict[str, Any]]]:
    raw_config = load_json(path)

    if "instances" not in raw_config:
        instance_name = (
            raw_config.get("name")
            or raw_config.get("instance_id")
            or raw_config.get("servername")
            or path.stem
        )
        return [(path, str(instance_name), raw_config)]

    shared_defaults = {
        key: value for key, value in raw_config.items() if key != "instances"
    }

    instances = []
    for index, instance_config in enumerate(raw_config["instances"], start=1):
        merged_config = {**shared_defaults, **instance_config}

        if merged_config.get("enabled", True) is False:
            continue

        instance_name = (
            merged_config.get("name")
            or merged_config.get("instance_id")
            or merged_config.get("servername")
            or f"{path.stem}_{index}"
        )

        instances.append((path, str(instance_name), merged_config))

    return instances


def load_configs(args: argparse.Namespace) -> List[Tuple[Path, str, Dict[str, Any]]]:
    if args.config_dir:
        config_dir = Path(args.config_dir)
        if not config_dir.exists() or not config_dir.is_dir():
            raise FileNotFoundError(f"Config directory does not exist: {config_dir}")

        configs: List[Tuple[Path, str, Dict[str, Any]]] = []
        for config_path in sorted(config_dir.glob("*.json")):
            configs.extend(load_config_file(config_path))

        if not configs:
            raise ValueError(f"No enabled *.json configs found in: {config_dir}")

        return configs

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")

    return load_config_file(config_path)


def validate_config(config: Dict[str, Any], config_path: Path, instance_name: str) -> None:
    missing_keys = [
        key
        for key in REQUIRED_CONFIG_KEYS
        if key not in config or config[key] in (None, "")
    ]

    if missing_keys:
        joined_keys = ", ".join(missing_keys)
        raise ValueError(
            f"Config '{config_path}' instance '{instance_name}' is missing required keys: {joined_keys}"
        )


def build_backup_config(config: Dict[str, Any]) -> BackupConfig:
    return BackupConfig(
        source=config["source"],
        target=config["target"],
        db_location=config["db_location"],
        servername=config["servername"],
        rstoollocation=config["rstoollocation"],
        temp_folder=config["temp_folder"],
        root_folder_id=config["root_folder_id"],
        backup_to_target=config.get("backup_to_target", False),
        backup_to_gdrive=config.get("backup_to_gdrive", True),
    )


def resolve_mode(args: argparse.Namespace, config: Dict[str, Any]) -> str:
    mode = args.mode or config.get("mode") or "edited"
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid backup mode '{mode}'. Expected one of: {', '.join(VALID_MODES)}")
    return mode


def resolve_model(args: argparse.Namespace, config: Dict[str, Any]) -> str | None:
    return args.model or config.get("model") or config.get("specific_model")


def run_backup_for_instance(
    config_path: Path,
    instance_name: str,
    config: Dict[str, Any],
    args: argparse.Namespace,
) -> None:
    validate_config(config, config_path, instance_name)

    log_path = setup_logging(Path(args.log_dir), instance_name)
    mode = resolve_mode(args, config)
    model = resolve_model(args, config)

    logging.info("=" * 80)
    logging.info("Revit Server backup started")
    logging.info(f"Instance: {instance_name}")
    logging.info(f"Config: {config_path}")
    logging.info(f"Mode: {mode}")
    logging.info(f"Log file: {log_path}")

    if mode == "selected" and not model:
        raise ValueError(
            f"Instance '{instance_name}' uses selected mode, but no model was provided. "
            "Use --model or add 'model'/'specific_model' to config."
        )

    backup_manager = BackupManager(build_backup_config(config))

    if mode == "all":
        backup_manager.backup_all_models()
    elif mode == "edited":
        backup_manager.backup_edited_models()
    elif mode == "selected":
        backup_manager.backup_specific_model(model)
    else:
        raise ValueError(f"Unsupported backup mode: {mode}")

    logging.info("Revit Server backup finished")


def main() -> int:
    args = parse_args()

    try:
        configs = load_configs(args)
    except Exception as error:
        setup_logging(Path(args.log_dir), "revit_backup")
        logging.error(f"Unable to load backup configs: {error}")
        return 1

    failures = 0

    for config_path, instance_name, config in configs:
        try:
            run_backup_for_instance(config_path, instance_name, config, args)
        except Exception as error:
            failures += 1
            logging.exception(f"Backup failed for instance '{instance_name}': {error}")

            if args.stop_on_error:
                break

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
