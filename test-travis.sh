set -e
set -x

if [[ $INTEGRATION_TARGET = '' ]]; then
  py.test --cov-report term-missing --cov regparser
  flake8 .
else
  if [[ $DOCKER_BUILD ]]; then
    docker build . -t eregs-parser
    MANAGE_CMD="docker run --rm -it -v eregs-cache:/app/cache -v output:/app/output --entrypoint ./manage.py eregs-parser"
  else
    MANAGE_CMD=./manage.py
  fi
  $MANAGE_CMD migrate
  $MANAGE_CMD integration_test uninstall
  $MANAGE_CMD integration_test install $INTEGRATION_TARGET
  $MANAGE_CMD integration_test build $INTEGRATION_TARGET
  $MANAGE_CMD integration_test compare $INTEGRATION_TARGET
fi
