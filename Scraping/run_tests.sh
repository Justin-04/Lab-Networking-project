ROUNDS=3
PAUSE_METHOD=60
PAUSE_ROUND=900

mkdir -p pcaps logs runs
sudo -v || exit 1
while true; do sudo -n true; sleep 60; done 2>/dev/null &
KEEP=$!
trap 'kill $KEEP 2>/dev/null' EXIT

for r in $(seq 1 $ROUNDS); do
  for m in api bs4 selenium; do
    echo "=== Round $r/$ROUNDS - $m - $(date +%T) ==="
    sudo tcpdump -i any -U -w pcaps/${m}_run$r.pcap 'port 443 or port 80 or port 53' 2>/dev/null &
    sleep 2
    (while true; do echo "--- $(date +%T)"; ss -tnp | grep -E 'python|chrome'; sleep 1; done) > logs/${m}_run${r}_ss.txt &
    SS=$!

    python hn_$m.py

    sleep 2
    kill $SS
    sudo pkill -INT -f "pcaps/${m}_run$r.pcap"
    sleep 1
    sudo chown $USER pcaps/${m}_run$r.pcap
    cp hn_$m.csv runs/hn_${m}_run$r.csv
    if [ $m != selenium ]; then sleep $PAUSE_METHOD; fi
  done
  if [ $r -lt $ROUNDS ]; then echo "Pause of $PAUSE_ROUND s before the next round..."; sleep $PAUSE_ROUND; fi
done
capinfos -T -m -c -d -u pcaps/*.pcap > pcaps/summary.csv
echo
echo "Done. Capture summary: pcaps/summary.csv"
echo "This session in metrics.csv:"
tail -n $((ROUNDS*3)) metrics.csv
