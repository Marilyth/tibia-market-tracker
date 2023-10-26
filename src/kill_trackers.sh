# Kills all running tracker processes, i.e. those that show up as "sudo python3 extract.py" in the process list.
pids=$(ps -aux | grep "sudo python3 extract.py" | grep -v grep | awk '{print $2}')

# Kill all tracker processes
for pid in $pids
do
    kill -9 $pid
done

# Kill all Tibia processes, i.e. those that show up as "Tibia/bin/client" in the process list.
pids=$(ps -aux | grep "Tibia/bin/client" | grep -v grep | awk '{print $2}')

# Kill all Tibia processes
for pid in $pids
do
    kill -9 $pid
done

# Kill all Xephyr processes, i.e. those that show up as "Xephyr" in the process list.
pids=$(ps -aux | grep "Xephyr" | grep -v grep | awk '{print $2}')

# Kill all Xephyr processes
for pid in $pids
do
    kill -9 $pid
done