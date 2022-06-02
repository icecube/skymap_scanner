#!/bin/sh

# NOTE: put env vars here that make sense for any scenario (CI or local)

# SKYSCAN_TEST_EVENT=test_event_01
# SKYSCAN_TEST_EVENT_PATH=/mnt/test_event_01.i3
export PULSAR_CONTAINER=pulsar_local
export SKYSCAN_CONTAINER=skyscan-cloud
# SKYSCAN_EVENT=./tests/docker_scripts/event_HESE_2017-11-28.json
export SKYSCAN_CACHE_DIR=cache-dir
# SKYSCAN_EVENT=ic191001a_sim.i3
export SKYSCAN_EVENT_PKL=./tests/data/skyscan_data/realtime_events/-243122034428012599.pkl
export PULSAR_ADDRESS=localhost:6650
export PULSAR_AUTH=""
export SKYSCAN_DEBUG_DIR=debug-pkl-dir