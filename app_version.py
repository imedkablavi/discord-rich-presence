"""Build-time application version metadata.

Release workflows replace ``APP_VERSION`` from the Git tag before packaging.
Source/QA builds intentionally stay on a development version so they never
silently self-update over a developer checkout.
"""

APP_VERSION = "0.0.0-dev"
