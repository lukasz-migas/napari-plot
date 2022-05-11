@REM Use imagemagick to create icon.ico and icon.icns files
SET script_dir=%~dp0%
SET misc_dir=%script_dir%\..\misc
SET output_dir=%script_dir%\..\napari_plot\resources
CALL convert -background transparent %misc_dir%\logo.png -define icon:auto-resize=16,24,32,48,64,72,96,128,256 %misc_dir%\icon.ico
CALL convert -background transparent %misc_dir%\logo.png -define icon:auto-resize=16,24,32,48,64,72,96,128,256 %misc_dir%\icon.icns
@REM move files over to napari_plot/resources
XCOPY %misc_dir%\icon.ico %output_dir%\icon.ico /Y
XCOPY %misc_dir%\icon.icns %output_dir%\icon.icns /Y
