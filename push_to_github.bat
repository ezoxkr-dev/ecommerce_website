@echo off
echo Configuring Git and pushing to GitHub...
"C:\Program Files\Git\cmd\git.exe" config user.email "admin@ezoxkr.dev"
"C:\Program Files\Git\cmd\git.exe" config user.name "Ezox Admin"
"C:\Program Files\Git\cmd\git.exe" init
"C:\Program Files\Git\cmd\git.exe" add .
"C:\Program Files\Git\cmd\git.exe" commit -m "Initial commit"
"C:\Program Files\Git\cmd\git.exe" branch -M main
"C:\Program Files\Git\cmd\git.exe" remote add origin https://github.com/ezoxkr-dev/ecommerce_website.git 2>nul
"C:\Program Files\Git\cmd\git.exe" push -u origin main
echo.
echo Done!
pause
