set -e
set -x

if [[ $INTEGRATION_TARGET = '' ]]; then
  nosetests --with-cov --cov-report term-missing --cov regparser
  flake8 .
else
  eregs clear
  ./integration_test.py uninstall
  ./integration_test.py install $INTEGRATION_TARGET
  ./integration_test.py build $INTEGRATION_TARGET
  if [[ $TRAVIS_PULL_REQUEST = 'false' ]] && [[ $TRAVIS_BRANCH = 'master' ]] && [[ $TRAVIS_PYTHON_VERSION = '2.7' ]]; then
    ./integration_test.py upload $INTEGRATION_TARGET
  else
    ./integration_test.py compare $INTEGRATION_TARGET
  fi
fi
