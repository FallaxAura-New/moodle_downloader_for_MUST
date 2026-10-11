@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
pushd "%~dp0" >nul 2>&1
if errorlevel 1 goto directory_error

set "MUST_PYTHON="
set "MUST_PYTHON_ARGS="
if exist ".venv\Scripts\python.exe" goto use_venv
where py >nul 2>&1
if errorlevel 1 goto try_python
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto try_python
set "MUST_PYTHON=py"
set "MUST_PYTHON_ARGS=-3"
goto check_dependencies

:try_python
where python >nul 2>&1
if errorlevel 1 goto python_error
set "MUST_PYTHON=python"
goto check_version

:use_venv
set "MUST_PYTHON=%CD%\.venv\Scripts\python.exe"

:check_version
"%MUST_PYTHON%" %MUST_PYTHON_ARGS% -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto python_error

:check_dependencies
"%MUST_PYTHON%" %MUST_PYTHON_ARGS% -c "import requests, bs4, selenium, rich" >nul 2>&1
if errorlevel 1 goto dependency_error
"%MUST_PYTHON%" %MUST_PYTHON_ARGS% -m moodle_scraper.windows_launcher %*
set "MUST_EXIT_CODE=%ERRORLEVEL%"
goto finish

:python_error
>&2 echo MUST Moodle: 请安装 Python 3.11 或更新版本，并检查项目的 .venv。
>&2 echo Python 3.11+ is required. Check Python and the project .venv.
goto failure

:dependency_error
>&2 echo MUST Moodle: 当前 Python 环境缺少依赖，请先运行以下命令：
>&2 echo Missing dependencies. Run:
>&2 echo "%MUST_PYTHON%" %MUST_PYTHON_ARGS% -m pip install -r requirements.txt
goto failure

:failure
set "MUST_EXIT_CODE=1"
if "%~1"=="" pause

:finish
popd
endlocal & exit /b %MUST_EXIT_CODE%

:directory_error
>&2 echo MUST Moodle: 无法进入启动器所在目录。Cannot open the launcher directory.
if "%~1"=="" pause
endlocal & exit /b 1
