# 本地启动脚本模板
#
# 用法：
#   1. 复制一份并去掉 .example：copy start.example.ps1 start.ps1
#   2. 把下面的 <...> 占位符替换成你自己的值
#   3. 执行 .\start.ps1
#
# start.ps1 已在 .gitignore 中排除，不会被提交。
# 这个模板文件本身可以安全提交，请勿在里面填真实密钥。

$env:ANTHROPIC_BASE_URL="<你的 API 地址>"
$env:ANTHROPIC_AUTH_TOKEN="<你的 API Key>"
$env:ANTHROPIC_MODEL="<默认模型>"
$env:ANTHROPIC_DEFAULT_OPUS_MODEL="<Opus 模型>"
$env:ANTHROPIC_DEFAULT_SONNET_MODEL="<Sonnet 模型>"
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL="<Haiku 模型>"
$env:CLAUDE_CODE_SUBAGENT_MODEL="<子代理模型>"
$env:CLAUDE_CODE_EFFORT_LEVEL="high"
claude
