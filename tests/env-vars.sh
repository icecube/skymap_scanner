#!/bin/bash
set -ex

export REALTIME_EVENTS_DIR=/home/runner/work/skymap_scanner/skymap_scanner/tests/data/realtime_events
export SKYSCAN_CACHE_DIR=/home/runner/work/skymap_scanner/skymap_scanner/cache-dir
export SKYSCAN_OUTPUT_DIR=/home/runner/work/skymap_scanner/skymap_scanner/output-dir
export SKYSCAN_BROKER_CLIENT=rabbitmq
# note=auth env vars are in job(s)
export EWMS_PILOT_TASK_TIMEOUT=600
export SKYSCAN_DEBUG_DIR=debug-pkl-dir
export SKYSCAN_MQ_TIMEOUT_TO_CLIENTS=60
# export SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS=60  # use default
export SKYSCAN_MQ_CLIENT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE=120
export SKYSCAN_DOCKER_PULL_ALWAYS=0
export SKYSCAN_DOCKER_IMAGE_TAG=local
export SKYSCAN_MINI_TEST='yes'
export SKYSCAN_LOG=DEBUG
export SKYSCAN_LOG_THIRD_PARTY=INFO
export CLIENT_STARTER_WAIT_FOR_STARTUP_JSON=120
