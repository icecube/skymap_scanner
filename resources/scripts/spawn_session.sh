#!/bin/bash
export TMUX=""
export SESSION=$1
export ENV_PATH=$2
echo Spawning new session with following command
echo "tmux new-session -d -s $SESSION bash $ENV_PATH/skymap_scanner/resources/scripts/start_env.sh $ENV_PATH $3"
tmux new-session -d -s $SESSION "bash $ENV_PATH/skymap_scanner/resources/scripts/start_env.sh $ENV_PATH $3"

