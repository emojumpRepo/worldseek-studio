from enum import Enum


class MESSAGES(str, Enum):
    DEFAULT = lambda msg="": f"{msg if msg else ''}"
    MODEL_ADDED = lambda model="": f"模型 '{model}' 已成功添加。"
    MODEL_DELETED = (
        lambda model="": f"模型 '{model}' 已成功删除。"
    )


class WEBHOOK_MESSAGES(str, Enum):
    DEFAULT = lambda msg="": f"{msg if msg else ''}"
    USER_SIGNUP = lambda username="": (
        f"新用户已注册: {username}" if username else "新用户已注册"
    )


class ERROR_MESSAGES(str, Enum):
    def __str__(self) -> str:
        return super().__str__()

    DEFAULT = (
        lambda err="": f'{"Something went wrong :/" if err == "" else "[ERROR: " + str(err) + "]"}'
    )
    ENV_VAR_NOT_FOUND = "没有找到所需的环境变量。终止了。"
    CREATE_USER_ERROR = "哦!创建账户时出了问题。请稍后再试。如果问题仍然存在，请联系技术支持。"
    DELETE_USER_ERROR = "哦!在尝试删除用户时出了问题。请再试一次。"
    EMAIL_MISMATCH = "哦!这个邮箱与您提供商注册的邮箱不匹配。请检查您的邮箱并再试一次。"
    EMAIL_TAKEN = "哦!这个邮箱已经注册了。请使用您的现有账户登录或选择另一个邮箱开始新的旅程。"
    USERNAME_TAKEN = (
        "哦!这个用户名已经注册了。请选择另一个用户名。"
    )
    PASSWORD_TOO_LONG = "哦!您输入的密码太长了。请确保您的密码小于72字节。"
    COMMAND_TAKEN = "哦!这个命令已经注册了。请选择另一个命令字符串。"
    FILE_EXISTS = "哦!这个文件已经注册了。请选择另一个文件。"

    ID_TAKEN = "哦!这个ID已经注册了。请选择另一个ID字符串。"
    MODEL_ID_TAKEN = "哦!这个模型ID已经注册了。请选择另一个模型ID字符串。"
    NAME_TAG_TAKEN = "哦!这个名称标签已经注册了。请选择另一个名称标签字符串。"

    INVALID_TOKEN = (
        "您的会话已过期或令牌无效。请重新登录。"
    )
    INVALID_CRED = "您提供的邮箱或密码不正确。请检查是否有拼写错误并再试一次。"
    INVALID_EMAIL_FORMAT = "您输入的邮箱格式不正确。请检查并确保您使用的是有效的邮箱地址（例如，您的名字@example.com）。"
    INVALID_PASSWORD = (
        "您提供的密码不正确。请检查是否有拼写错误并再试一次。"
    )
    INVALID_TRUSTED_HEADER = "您的提供商没有提供受信任的头部。请联系您的管理员寻求帮助。"

    EXISTING_USERS = "您不能关闭认证，因为存在现有用户。如果您想禁用WEBUI_AUTH，请确保您的网络界面没有现有用户并且是一个全新的安装。"

    UNAUTHORIZED = "401 Unauthorized"
    ACCESS_PROHIBITED = "您没有权限访问此资源。请联系您的管理员寻求帮助。"
    ACTION_PROHIBITED = (
        "请求的操作已被限制为安全措施。"
    )

    FILE_NOT_SENT = "FILE_NOT_SENT"
    FILE_NOT_SUPPORTED = "哦!似乎您尝试上传的文件格式不受支持。请上传一个受支持的格式并再试一次。"

    NOT_FOUND = "我们找不到您正在寻找的内容 :/"
    USER_NOT_FOUND = "我们找不到您正在寻找的内容 :/"
    API_KEY_NOT_FOUND = "哦!似乎出了点问题。API密钥缺失。请确保提供有效的API密钥以访问此功能。"
    API_KEY_NOT_ALLOWED = "在环境中禁用了API密钥的使用。"

    MALICIOUS = "检测到异常活动，请稍后再试。"

    PANDOC_NOT_INSTALLED = "Pandoc未安装在服务器上。请联系您的管理员寻求帮助。"
    INCORRECT_FORMAT = (
        lambda err="": f"格式不正确。请使用正确的格式{err}"
    )
    RATE_LIMIT_EXCEEDED = "API速率限制已超出。"

    MODEL_NOT_FOUND = lambda name="": f"模型 '{name}' 未找到"
    OPENAI_NOT_FOUND = lambda name="": "OpenAI API 未找到"
    OLLAMA_NOT_FOUND = "WebUI 无法连接到 Ollama"
    CREATE_API_KEY_ERROR = "哦!在创建您的API密钥时出了问题。请稍后再试。如果问题仍然存在，请联系支持寻求帮助。"
    API_KEY_CREATION_NOT_ALLOWED = "在环境中禁用了API密钥的创建。"

    EMPTY_CONTENT = "提供的文本为空。请确保在继续之前有文本或数据。"

    DB_NOT_SQLITE = "此功能仅在运行SQLite数据库时可用。"

    INVALID_URL = (
        "哦!您提供的URL无效。请检查并再试一次。"
    )

    WEB_SEARCH_ERROR = (
        lambda err="": f"{err if err else '哦!在搜索网络时出了问题。'}"
    )

    OLLAMA_API_DISABLED = (
        "Ollama API 已禁用。请启用它以使用此功能。"
    )

    FILE_TOO_LARGE = (
        lambda size="": f"哦!您尝试上传的文件太大了。请上传一个小于 {size} 的文件。"
    )

    DUPLICATE_CONTENT = (
        "检测到重复内容。请提供独特的内容以继续。"
    )
    FILE_NOT_PROCESSED = "提取的内容不可用于此文件。请确保在继续之前处理文件。"


class TASKS(str, Enum):
    def __str__(self) -> str:
        return super().__str__()

    DEFAULT = lambda task="": f"{task if task else 'generation'}"
    TITLE_GENERATION = "title_generation"
    TAGS_GENERATION = "tags_generation"
    EMOJI_GENERATION = "emoji_generation"
    QUERY_GENERATION = "query_generation"
    IMAGE_PROMPT_GENERATION = "image_prompt_generation"
    AUTOCOMPLETE_GENERATION = "autocomplete_generation"
    FUNCTION_CALLING = "function_calling"
    MOA_RESPONSE_GENERATION = "moa_response_generation"
