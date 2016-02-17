set -e
set -x

if [[ $INTEGRATION_TARGET = '' ]]; then
  nosetests --with-cov --cov-report term-missing --cov regparser
  flake8 .
else
  eregs clear
  ./integration_test.py install $INTEGRATION_TARGET
  ./integration_test.py test $INTEGRATION_TARGET
fi
