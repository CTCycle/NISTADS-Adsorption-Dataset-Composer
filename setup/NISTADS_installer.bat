@echo off

:: [CHECK CUSTOM ENVIRONMENTS] 
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Check if NISTADS environment is available or use custom environment
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
call conda config --add channels conda-forge
call conda info --envs | findstr "NISTADS"
if %ERRORLEVEL%==0 (
    echo NISTADS environment detected
    call conda activate NISTADS
    goto :dependencies
) else (
    echo NISTADS environment has not been found, it will now be created using python 3.11
    echo Depending on your internet connection, this may take a while!
    call conda create -n NISTADS python=3.11 -y
    call conda activate NISTADS
    goto :dependencies
)

:: [INSTALL DEPENDENCIES] 
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Install dependencies to python environment
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:dependencies
echo.
echo Install python libraries and packages
call pip install torch==2.5.0+cu121 pip install torchvision==0.20.0+cu121 --extra-index-url https://download.pytorch.org/whl/cu121
call pip install tensorflow-cpu==2.18.0 keras==3.6.0
call pip install transformers==4.43.3 matplotlib==3.9.2 seaborn==0.13.2 scikit-learn==1.5.1
call pip install numpy==2.1.2 pandas==2.2.3 tqdm==4.66.4 pubchempy==1.0.4 

:: [INSTALL TRITON] 
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Install dependencies to python environment
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo Installing triton from windows wheel
cd triton
call pip install triton-3.1.0-cp311-cp311-win_amd64.whl
cd ..

:: [INSTALLATION OF PYDOT/PYDOTPLUS]
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Install pydot/pydotplus for graphic model visualization
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: 
echo Installing pydot and pydotplus...
call conda install pydot -y
call conda install pydotplus -y

:: [INSTALL PROJECT IN EDITABLE MODE] 
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Install project in developer mode
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo Install utils packages in editable mode
call cd .. && pip install -e . --use-pep517 && cd NISTADS

:: [CLEAN CACHE] 
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Clean packages cache
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo.
echo Cleaning conda and pip cache 
call conda clean --all -y
call pip cache purge

:: [SHOW LIST OF INSTALLED DEPENDENCIES]
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Show installed dependencies
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: 
echo.
echo List of installed dependencies:
call conda list

echo.
echo Installation complete. You can now run NISTADS on this system!
pause
