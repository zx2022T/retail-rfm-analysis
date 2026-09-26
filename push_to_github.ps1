# ============================================================
#  一键推送到 GitHub
#  用法：右键本文件 → 使用 PowerShell 运行
#        或在 PowerShell 里执行： .\push_to_github.ps1
# ============================================================

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "=== 零售用户价值分析 · 推送到 GitHub ===" -ForegroundColor Cyan
Write-Host ""

# ---------- 1. 前置检查 ----------
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "未检测到 git，请先安装 Git for Windows：https://git-scm.com/" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Host "当前目录还不是 git 仓库，正在初始化..." -ForegroundColor Yellow
    git init -b main
    git add -A
    git commit -m "feat: 零售用户价值分析项目"
}

# ---------- 2. 收集信息 ----------
$user = Read-Host "GitHub 用户名（例如 tangxiaozhuang）"
if ([string]::IsNullOrWhiteSpace($user)) {
    Write-Host "用户名不能为空" -ForegroundColor Red
    exit 1
}

$repo = Read-Host "仓库名（默认 retail-rfm-analysis）"
if ([string]::IsNullOrWhiteSpace($repo)) { $repo = "retail-rfm-analysis" }

Write-Host ""
Write-Host "使用哪种方式？" -ForegroundColor Yellow
Write-Host "  1) HTTPS（推荐，浏览器登录一次即可）"
Write-Host "  2) SSH（需已配置 SSH key）"
$mode = Read-Host "请输入 1 或 2（默认 1）"
if ([string]::IsNullOrWhiteSpace($mode)) { $mode = "1" }

if ($mode -eq "2") {
    $url = "git@github.com:$user/$repo.git"
} else {
    $url = "https://github.com/$user/$repo.git"
}

# ---------- 3. 确认 ----------
Write-Host ""
Write-Host "即将推送到：$url" -ForegroundColor Green
Write-Host "请先确认你已在 GitHub 网页上创建了这个【空仓库】（不要勾选 README/LICENSE）" -ForegroundColor Yellow
$ok = Read-Host "已创建好了吗？(y/n)"
if ($ok -ne "y" -and $ok -ne "Y") {
    Write-Host "请先去 https://github.com/new 创建空仓库后再运行本脚本" -ForegroundColor Yellow
    exit 0
}

# ---------- 4. 执行 ----------
Write-Host ""
$existing = git remote get-url origin 2>$null
if ($existing) {
    Write-Host "已存在 remote origin：$existing，将更新为 $url"
    git remote set-url origin $url
} else {
    git remote add origin $url
}

git branch -M main

Write-Host "推送中..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "推送成功！" -ForegroundColor Green
    Write-Host "打开查看：https://github.com/$user/$repo" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "推送失败，常见原因：" -ForegroundColor Red
    Write-Host "  1. GitHub 上还没有这个空仓库 → 去 https://github.com/new 创建（不要初始化 README）"
    Write-Host "  2. 认证失败 → HTTPS 方式会弹浏览器让你登录，按提示完成即可"
    Write-Host "  3. 网络问题 → 检查代理或稍后重试"
}

Write-Host ""
Read-Host "按回车键退出"
