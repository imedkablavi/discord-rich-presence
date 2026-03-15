#!/usr/bin/env python3
import argparse
import sys
import logging
from pathlib import Path
from config import Config
from tray_icon import run_with_tray
from core.presence_service import PresenceService

def main():
    parser = argparse.ArgumentParser(description='Discord Rich Presence Service')
    parser.add_argument('--config', type=Path, default=None)
    parser.add_argument('--privacy', choices=['off', 'balanced', 'strict'])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--tray', action='store_true')
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        config = Config(args.config)
        if args.privacy:
            config.set('privacy.mode', args.privacy)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        sys.exit(1)
        
    service = PresenceService(config=config, dry_run=args.dry_run, once=args.once)
    if args.tray or config.get('system.start_minimized', False):
        run_with_tray(service.run, config, service.stop)
    else:
        service.run()

if __name__ == '__main__':
    main()
