rd /s /q dist
mkdir dist
python C:\Python27\Scripts\cxfreeze --icon=src\camera_pin_icon.ico --base-name=Win32GUI "src\photo_trail_mapper.py"
copy dist\photo_trail_mapper.exe "dist\photo trail mapper.exe"
del dist\photo_trail_mapper.exe
copy src\camera_pin_icon.ico dist
xcopy src\css dist\css\ /E /I
xcopy src\images dist\images\ /E /I
xcopy src\js dist\js\ /E /I
copy src\index.xhtml dist\index.xhtml
