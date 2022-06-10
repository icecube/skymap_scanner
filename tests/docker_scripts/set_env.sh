#!/bin/sh

# NOTE: put env vars here that make sense for any scenario (CI or local)

export PULSAR_CONTAINER=pulsar_local
export SKYSCAN_CONTAINER=skyscan-cloud
export SKYSCAN_CACHE_DIR=cache-dir
export REALTIME_EVENTS_DIR=./tests/data/skyscan_data/realtime_events/
export PULSAR_ADDRESS=localhost:6650
export PULSAR_AUTH=""
export SKYSCAN_DEBUG_DIR=debug-pkl-dir