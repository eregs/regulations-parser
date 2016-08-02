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
  if [[ $TRAVIS_PULL_REQUEST = 'false' ]] && [[ $TRAVIS_BRANCH = 'master' ]] && [[ $TRAVIS_PYTHON_VERSION = '2.7' ]]; then
    ./manage.py integration_test upload $INTEGRATION_TARGET
  else
    ./manage.py integration_test compare $INTEGRATION_TARGET
  fi
fi
