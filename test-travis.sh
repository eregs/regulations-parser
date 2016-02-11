set -e
set -x

if [[ $INTEGRATION_TARGET = '' ]]; then
  nosetests --with-cov --cov-report term-missing --cov regparser
  flake8 .
else
  eregs clear
  eregs integration_test $INTEGRATION_TARGET
fi
