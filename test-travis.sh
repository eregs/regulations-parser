set -e
set -x

./manage.py migrate

if [[ $INTEGRATION_TARGET = '' ]]; then
  py.test --cov-report term-missing --cov regparser
  flake8 .
else
  eregs clear
  ./manage.py integration_test uninstall
  ./manage.py integration_test install $INTEGRATION_TARGET
  ./manage.py integration_test build $INTEGRATION_TARGET
  ./manage.py integration_test compare $INTEGRATION_TARGET
fi
