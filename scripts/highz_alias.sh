# Custom aliases for HighZ Digital Spectrometer Control

# Run the spectrometer using pipenv
alias TakeSpecs='cd ~/highz-digitalspec && pipenv run python src/run_spectrometer.py --antenna "$@"'

# Navigate to the data storage directory (update path as needed)
alias GetSpecs='cd /media/peterson/INDURANCE'

# Quick way to enter the spectrometer virtual environment
alias SpecShell='cd ~/highz-digitalspec && pipenv shell'

# Run the spectrometer with the launcher script
alias TakeSpecsLauncher='~/highz-digitalspec/scripts/launcher.sh'
export PYTHONPATH=/home/peterson/highz-digitalspec/src:$PYTHONPATH

ControlState(){
    SRC_PATH=/home/peterson/highz-digitalspec
    export PIPENV_PIPFILE=$SRC_PATH/Pipfile
    pipenv run python $SRC_PATH/tools/gpio_test.py "$@"
}