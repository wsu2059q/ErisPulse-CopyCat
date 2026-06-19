from ErisPulse import sdk

DEFAULT_CONFIG = {
    "enabled": True,
    "trigger_count": 2
}


def load_config():
    """加载 CopyCat 模块配置"""
    config = sdk.config.getConfig("CopyCat")
    if not config:
        sdk.config.setConfig("CopyCat", DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    return config
