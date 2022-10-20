#!/bin/sh

# use m5n.8xlarge (32 cores), use submitter AMI

ssh -i ~/.ssh/claudiok.pem ubuntu@13.58.178.98
apt install tmux python3.7 python3-boto3
scp -i ~/.ssh/claudiok.pem ~/.ssh/claudiok.pem ubuntu@13.58.178.98:~/.ssh/claudiok.pem
scp -i ~/.ssh/claudiok.pem ~/.aws/credentials ubuntu@13.58.178.98:~/.aws/credentials
rsync -e "ssh -i ~/.ssh/claudiok.pem" -r --progress ./ ubuntu@13.58.178.98:~/skymap_scanner/
# change aws_ec2/submit_scan_to_ec2.py to python3.7

tmux new -s infra
tmux new -s submit

tmux attach -t infra
tmux attach -t submit

# ./aws_ec2/submit_scan_to_ec2.py --token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token` --num 5000 --collector-num 0
./aws_ec2/submit_scan_to_ec2.py --token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token` --num 32 --collector-num 0
./aws_ec2/submit_scan_to_ec2.py --token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token` --num 0 --collector-num 4


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00118435_Subrun00000000_00000144_event58198553.i3.zst -n Run00118435 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00118435 -o /mnt/output_files/Run00118435_event58198553_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00118435          at (nside,pix)=(16,492) [llh=5546.95]: dec=41.81deg RA=70.31deg / 4.69hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00118435_Subrun00000000_00000144_event58198553.i3.zst -n Run00118435 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,492,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00118435 -o /mnt/output_files/Run00118435_event58198553_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00118435          at (nside,pix)=(128,34145) [llh=5113.44]: dec=40.62deg RA=68.20deg / 4.55hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00118435_Subrun00000000_00000144_event58198553.i3.zst -n Run00118435 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,34145,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00118435 -o /mnt/output_files/Run00118435_event58198553_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00118435          at (nside,pix)=(1024,2190088) [llh=5112.87]: dec=40.67deg RA=68.20deg / 4.55hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00118435_event58198553_scanned1024.i3.zst



####################################################################



# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00118741_Subrun00000000_00000109_event43101116.i3.zst -n Run00118741 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00118741 -o /mnt/output_files/Run00118741_event43101116_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00118741          at (nside,pix)=(16,1679) [llh=2344.50]: dec=-4.78deg RA=267.19deg / 17.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00118741_Subrun00000000_00000109_event43101116.i3.zst -n Run00118741 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1679,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00118741 -o /mnt/output_files/Run00118741_event43101116_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00118741          at (nside,pix)=(128,106108) [llh=2338.89]: dec=-4.48deg RA=267.19deg / 17.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00118741_Subrun00000000_00000109_event43101116.i3.zst -n Run00118741 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,106108,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00118741 -o /mnt/output_files/Run00118741_event43101116_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00118741          at (nside,pix)=(1024,6779870) [llh=2337.27]: dec=-4.44deg RA=267.01deg / 17.80hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00118741_event43101116_scanned1024.i3.zst
CHECK!


####################################################################



# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00120045_Subrun00000000_00000057_event22615214.i3.zst -n Run00120045 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00120045 -o /mnt/output_files/Run00120045_event22615214_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00120045          at (nside,pix)=(16,2999) [llh=1566.60]: dec=-72.39deg RA=172.50deg / 11.50hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00120045_Subrun00000000_00000057_event22615214.i3.zst -n Run00120045 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,2999,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00120045 -o /mnt/output_files/Run00120045_event22615214_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00120045          at (nside,pix)=(128,191397) [llh=1531.62]: dec=-71.28deg RA=165.00deg / 11.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2011_data_Run00120045_Subrun00000000_00000057_event22615214.i3.zst -n Run00120045 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,191397,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00120045 -o /mnt/output_files/Run00120045_event22615214_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00120045          at (nside,pix)=(1024,12258028) [llh=1531.31]: dec=-71.51deg RA=165.37deg / 11.02hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00120045_event22615214_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00120708_Subrun00000000_00000146_event53550535.i3.zst -n Run00120708 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00120708 -o /mnt/output_files/Run00120708_event53550535_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00120708          at (nside,pix)=(16,1004) [llh=2747.53]: dec=19.47deg RA=70.31deg / 4.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00120708_Subrun00000000_00000146_event53550535.i3.zst -n Run00120708 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1004,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00120708 -o /mnt/output_files/Run00120708_event53550535_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00120708          at (nside,pix)=(128,64868) [llh=2743.47]: dec=19.79deg RA=70.31deg / 4.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00120708_Subrun00000000_00000146_event53550535.i3.zst -n Run00120708 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,64868,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00120708 -o /mnt/output_files/Run00120708_event53550535_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00120708          at (nside,pix)=(1024,4160291) [llh=2742.30]: dec=19.79deg RA=70.62deg / 4.71hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00120708_event53550535_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121761_Subrun00000000_00000115_event41853263.i3.zst -n Run00121761 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00121761 -o /mnt/output_files/Run00121761_event41853263_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121761          at (nside,pix)=(16,40) [llh=1411.09]: dec=75.34deg RA=9.00deg / 0.60hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121761_Subrun00000000_00000115_event41853263.i3.zst -n Run00121761 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,40,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00121761 -o /mnt/output_files/Run00121761_event41853263_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121761          at (nside,pix)=(128,3615) [llh=1405.67]: dec=74.23deg RA=7.33deg / 0.49hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121761_Subrun00000000_00000115_event41853263.i3.zst -n Run00121761 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,3615,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00121761 -o /mnt/output_files/Run00121761_event41853263_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121761          at (nside,pix)=(1024,238769) [llh=1405.42]: dec=74.14deg RA=7.67deg / 0.51hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00121761_event41853263_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121762_Subrun00000000_00000157_event56963417.i3.zst -n Run00121762 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00121762 -o /mnt/output_files/Run00121762_event56963417_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121762          at (nside,pix)=(16,1618) [llh=1390.05]: dec=-2.39deg RA=281.25deg / 18.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121762_Subrun00000000_00000157_event56963417.i3.zst -n Run00121762 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1618,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00121762 -o /mnt/output_files/Run00121762_event56963417_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121762          at (nside,pix)=(128,101519) [llh=1375.29]: dec=-1.79deg RA=280.90deg / 18.73hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121762_Subrun00000000_00000157_event56963417.i3.zst -n Run00121762 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,101519,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00121762 -o /mnt/output_files/Run00121762_event56963417_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121762          at (nside,pix)=(1024,6501495) [llh=1373.86]: dec=-1.90deg RA=280.46deg / 18.70hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00121762_event56963417_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121769_Subrun00000000_00000111_event40349510.i3.zst -n Run00121769 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00121769 -o /mnt/output_files/Run00121769_event40349510_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121769          at (nside,pix)=(16,1631) [llh=2986.26]: dec=-2.39deg RA=354.38deg / 23.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121769_Subrun00000000_00000111_event40349510.i3.zst -n Run00121769 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1631,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00121769 -o /mnt/output_files/Run00121769_event40349510_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121769          at (nside,pix)=(128,102134) [llh=2945.66]: dec=-2.09deg RA=352.97deg / 23.53hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121769_Subrun00000000_00000111_event40349510.i3.zst -n Run00121769 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,102134,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00121769 -o /mnt/output_files/Run00121769_event40349510_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121769          at (nside,pix)=(1024,6510512) [llh=2944.79]: dec=-1.98deg RA=352.97deg / 23.53hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00121769_event40349510_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121840_Subrun00000000_00000173_event62872761.i3.zst -n Run00121840 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00121840 -o /mnt/output_files/Run00121840_event62872761_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121840          at (nside,pix)=(16,1896) [llh=8900.62]: dec=-14.48deg RA=47.81deg / 3.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121840_Subrun00000000_00000173_event62872761.i3.zst -n Run00121840 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1896,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00121840 -o /mnt/output_files/Run00121840_event62872761_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121840          at (nside,pix)=(128,120644) [llh=8211.44]: dec=-13.25deg RA=48.16deg / 3.21hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00121840_Subrun00000000_00000173_event62872761.i3.zst -n Run00121840 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,120644,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00121840 -o /mnt/output_files/Run00121840_event62872761_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00121840          at (nside,pix)=(1024,7739942) [llh=8192.07]: dec=-13.32deg RA=48.38deg / 3.23hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00121840_event62872761_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122055_Subrun00000000_00000015_event5809789.i3.zst  -n Run00122055 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122055 -o /mnt/output_files/Run00122055_event5809789_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122055          at (nside,pix)=(16,304) [llh=1541.91]: dec=54.34deg RA=303.75deg / 20.25hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122055_Subrun00000000_00000015_event5809789.i3.zst  -n Run00122055 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,304,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122055 -o /mnt/output_files/Run00122055_event5809789_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122055          at (nside,pix)=(128,18180) [llh=1540.68]: dec=54.72deg RA=303.63deg / 20.24hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122055_Subrun00000000_00000015_event5809789.i3.zst  -n Run00122055 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,18180,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122055 -o /mnt/output_files/Run00122055_event5809789_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122055          at (nside,pix)=(1024,1159285) [llh=1540.38]: dec=54.68deg RA=303.41deg / 20.23hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122055_event5809789_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122060_Subrun00000000_00000154_event56194427.i3.zst -n Run00122060 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122060 -o /mnt/output_files/Run00122060_event56194427_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122060          at (nside,pix)=(16,994) [llh=1510.73]: dec=19.47deg RA=14.06deg / 0.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122060_Subrun00000000_00000154_event56194427.i3.zst -n Run00122060 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,994,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122060 -o /mnt/output_files/Run00122060_event56194427_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122060          at (nside,pix)=(128,63763) [llh=1446.35]: dec=20.42deg RA=13.36deg / 0.89hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122060_Subrun00000000_00000154_event56194427.i3.zst -n Run00122060 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,63763,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122060 -o /mnt/output_files/Run00122060_event56194427_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122060          at (nside,pix)=(1024,4073625) [llh=1443.68]: dec=20.62deg RA=13.45deg / 0.90hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122060_event56194427_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122152_Subrun00000000_00000083_event30701331.i3.zst -n Run00122152 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122152 -o /mnt/output_files/Run00122152_event30701331_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122152          at (nside,pix)=(16,958) [llh=1394.23]: dec=22.02deg RA=168.75deg / 11.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122152_Subrun00000000_00000083_event30701331.i3.zst -n Run00122152 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,958,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122152 -o /mnt/output_files/Run00122152_event30701331_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122152          at (nside,pix)=(128,63470) [llh=1356.62]: dec=20.74deg RA=167.70deg / 11.18hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122152_Subrun00000000_00000083_event30701331.i3.zst -n Run00122152 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,63470,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122152 -o /mnt/output_files/Run00122152_event30701331_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122152          at (nside,pix)=(1024,4071285) [llh=1356.34]: dec=20.66deg RA=167.83deg / 11.19hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122152_event30701331_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122154_Subrun00000000_00000018_event6905361.i3.zst  -n Run00122154 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122154 -o /mnt/output_files/Run00122154_event6905361_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122154          at (nside,pix)=(16,1377) [llh=1097.84]: dec=4.78deg RA=8.44deg / 0.56hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122154_Subrun00000000_00000018_event6905361.i3.zst  -n Run00122154 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1377,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122154 -o /mnt/output_files/Run00122154_event6905361_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122154          at (nside,pix)=(128,90890) [llh=1095.95]: dec=4.18deg RA=7.38deg / 0.49hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122154_Subrun00000000_00000018_event6905361.i3.zst  -n Run00122154 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,90890,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122154 -o /mnt/output_files/Run00122154_event6905361_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122154          at (nside,pix)=(1024,5826644) [llh=1095.90]: dec=4.22deg RA=7.38deg / 0.49hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122154_event6905361_scanned1024.i3.zst
CHECK!


####################################################################


# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122160_Subrun00000000_00000144_event52726834.i3.zst -n Run00122160 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122160 -o /mnt/output_files/Run00122160_event52726834_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122160          at (nside,pix)=(16,829) [llh=1582.78]: dec=27.28deg RA=163.12deg / 10.88hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122160_Subrun00000000_00000144_event52726834.i3.zst -n Run00122160 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,829,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122160 -o /mnt/output_files/Run00122160_event52726834_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122160          at (nside,pix)=(128,50152) [llh=1567.71]: dec=29.31deg RA=163.48deg / 10.90hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2012_data_Run00122160_Subrun00000000_00000144_event52726834.i3.zst -n Run00122160 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,50152,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122160 -o /mnt/output_files/Run00122160_event52726834_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122160          at (nside,pix)=(1024,3198789) [llh=1567.43]: dec=29.44deg RA=163.56deg / 10.90hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122160_event52726834_scanned1024.i3.zst
CHECK!


####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122316_Subrun00000000_00000135_event49995489.i3.zst -n Run00122316 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122316   -o /mnt/output_files/Run00122316_event49995489_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122316          at (nside,pix)=(16,860) [llh=1652.43]: dec=27.28deg RA=337.50deg / 22.50hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122316_Subrun00000000_00000135_event49995489.i3.zst -n Run00122316 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,860,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122316   -o /mnt/output_files/Run00122316_event49995489_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122316          at (nside,pix)=(128,55008) [llh=1648.06]: dec=26.28deg RA=337.50deg / 22.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122316_Subrun00000000_00000135_event49995489.i3.zst -n Run00122316 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,55008,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122316   -o /mnt/output_files/Run00122316_event49995489_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122316          at (nside,pix)=(1024,3512067) [llh=1647.38]: dec=26.24deg RA=337.76deg / 22.52hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122316_event49995489_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122318_Subrun00000000_00000058_event21601607.i3.zst -n Run00122318 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122318   -o /mnt/output_files/Run00122318_event21601607_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122318          at (nside,pix)=(16,1496) [llh=1548.06]: dec=2.39deg RA=315.00deg / 21.00hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122318_Subrun00000000_00000058_event21601607.i3.zst -n Run00122318 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1496,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122318   -o /mnt/output_files/Run00122318_event21601607_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122318          at (nside,pix)=(128,94916) [llh=1487.53]: dec=2.09deg RA=317.81deg / 21.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122318_Subrun00000000_00000058_event21601607.i3.zst -n Run00122318 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,94916,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122318   -o /mnt/output_files/Run00122318_event21601607_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122318          at (nside,pix)=(1024,6063644) [llh=1486.71]: dec=2.09deg RA=317.50deg / 21.17hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122318_event21601607_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122361_Subrun00000000_00000125_event46565711.i3.zst -n Run00122361 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122361   -o /mnt/output_files/Run00122361_event46565711_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122361          at (nside,pix)=(16,872) [llh=1174.65]: dec=24.62deg RA=47.81deg / 3.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122361_Subrun00000000_00000125_event46565711.i3.zst -n Run00122361 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,872,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122361   -o /mnt/output_files/Run00122361_event46565711_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122361          at (nside,pix)=(128,58176) [llh=1153.56]: dec=23.97deg RA=45.35deg / 3.02hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122361_Subrun00000000_00000125_event46565711.i3.zst -n Run00122361 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,58176,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122361   -o /mnt/output_files/Run00122361_event46565711_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122361          at (nside,pix)=(1024,3746308) [llh=1153.32]: dec=23.85deg RA=45.35deg / 3.02hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122361_event46565711_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122469_Subrun00000000_00000086_event31925079.i3.zst -n Run00122469 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122469   -o /mnt/output_files/Run00122469_event31925079_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122469          at (nside,pix)=(16,1341) [llh=2423.76]: dec=7.18deg RA=163.12deg / 10.88hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122469_Subrun00000000_00000086_event31925079.i3.zst -n Run00122469 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1341,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122469   -o /mnt/output_files/Run00122469_event31925079_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122469          at (nside,pix)=(128,87529) [llh=2405.58]: dec=6.28deg RA=163.83deg / 10.92hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122469_Subrun00000000_00000086_event31925079.i3.zst -n Run00122469 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,87529,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122469   -o /mnt/output_files/Run00122469_event31925079_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122469          at (nside,pix)=(1024,5599052) [llh=2405.36]: dec=6.32deg RA=164.18deg / 10.95hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122469_event31925079_scanned1024.i3.zst
CHECK!


####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122604_Subrun00000000_00000046_event17469985.i3.zst -n Run00122604 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122604   -o /mnt/output_files/Run00122604_event17469985_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122604          at (nside,pix)=(16,1136) [llh=4986.87]: dec=14.48deg RA=92.81deg / 6.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122604_Subrun00000000_00000046_event17469985.i3.zst -n Run00122604 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1136,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122604   -o /mnt/output_files/Run00122604_event17469985_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122604          at (nside,pix)=(128,74117) [llh=4968.92]: dec=14.17deg RA=93.52deg / 6.23hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122604_Subrun00000000_00000046_event17469985.i3.zst -n Run00122604 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,74117,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122604   -o /mnt/output_files/Run00122604_event17469985_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122604          at (nside,pix)=(1024,4750378) [llh=4968.07]: dec=14.17deg RA=93.74deg / 6.25hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122604_event17469985_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122605_Subrun00000000_00000163_event60656774.i3.zst -n Run00122605 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122605   -o /mnt/output_files/Run00122605_event60656774_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122605          at (nside,pix)=(16,1468) [llh=1154.21]: dec=2.39deg RA=157.50deg / 10.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122605_Subrun00000000_00000163_event60656774.i3.zst -n Run00122605 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1468,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122605   -o /mnt/output_files/Run00122605_event60656774_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122605          at (nside,pix)=(128,91613) [llh=1112.03]: dec=3.88deg RA=155.39deg / 10.36hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122605_Subrun00000000_00000163_event60656774.i3.zst -n Run00122605 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,91613,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122605   -o /mnt/output_files/Run00122605_event60656774_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122605          at (nside,pix)=(1024,5881575) [llh=1111.37]: dec=3.73deg RA=155.35deg / 10.36hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122605_event60656774_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122663_Subrun00000000_00000158_event58987459.i3.zst -n Run00122663 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122663   -o /mnt/output_files/Run00122663_event58987459_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122663          at (nside,pix)=(16,1582) [llh=1086.22]: dec=-2.39deg RA=78.75deg / 5.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122663_Subrun00000000_00000158_event58987459.i3.zst -n Run00122663 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1582,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122663   -o /mnt/output_files/Run00122663_event58987459_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122663          at (nside,pix)=(128,102254) [llh=1080.54]: dec=-2.39deg RA=77.70deg / 5.18hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122663_Subrun00000000_00000158_event58987459.i3.zst -n Run00122663 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,102254,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122663   -o /mnt/output_files/Run00122663_event58987459_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122663          at (nside,pix)=(1024,6556534) [llh=1079.69]: dec=-2.43deg RA=77.87deg / 5.19hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122663_event58987459_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122768_Subrun00000000_00000103_event38570780.i3.zst -n Run00122768 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122768   -o /mnt/output_files/Run00122768_event38570780_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122768          at (nside,pix)=(16,1334) [llh=1015.19]: dec=7.18deg RA=123.75deg / 8.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122768_Subrun00000000_00000103_event38570780.i3.zst -n Run00122768 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1334,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122768   -o /mnt/output_files/Run00122768_event38570780_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122768          at (nside,pix)=(128,87471) [llh=1007.98]: dec=6.28deg RA=123.05deg / 8.20hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122768_Subrun00000000_00000103_event38570780.i3.zst -n Run00122768 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,87471,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122768   -o /mnt/output_files/Run00122768_event38570780_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122768          at (nside,pix)=(1024,5598582) [llh=1007.69]: dec=6.32deg RA=122.87deg / 8.19hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122768_event38570780_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122772_Subrun00000000_00000103_event38615684.i3.zst -n Run00122772 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122772   -o /mnt/output_files/Run00122772_event38615684_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122772          at (nside,pix)=(16,1350) [llh=804.58]: dec=7.18deg RA=213.75deg / 14.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122772_Subrun00000000_00000103_event38615684.i3.zst -n Run00122772 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1350,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122772   -o /mnt/output_files/Run00122772_event38615684_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122772          at (nside,pix)=(128,85042) [llh=794.09]: dec=7.78deg RA=215.51deg / 14.37hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122772_Subrun00000000_00000103_event38615684.i3.zst -n Run00122772 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,85042,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122772   -o /mnt/output_files/Run00122772_event38615684_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122772          at (nside,pix)=(1024,5443982) [llh=793.70]: dec=7.75deg RA=214.98deg / 14.33hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122772_event38615684_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122793_Subrun00000000_00000033_event12516001.i3.zst -n Run00122793 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122793   -o /mnt/output_files/Run00122793_event12516001_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122793          at (nside,pix)=(16,1207) [llh=2240.33]: dec=12.02deg RA=129.38deg / 8.62hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122793_Subrun00000000_00000033_event12516001.i3.zst -n Run00122793 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1207,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122793   -o /mnt/output_files/Run00122793_event12516001_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122793          at (nside,pix)=(128,75703) [llh=2212.04]: dec=13.25deg RA=129.02deg / 8.60hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122793_Subrun00000000_00000033_event12516001.i3.zst -n Run00122793 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,75703,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122793   -o /mnt/output_files/Run00122793_event12516001_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122793          at (nside,pix)=(1024,4836796) [llh=2211.85]: dec=13.36deg RA=129.02deg / 8.60hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122793_event12516001_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122818_Subrun00000000_00000045_event16944987.i3.zst -n Run00122818 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122818   -o /mnt/output_files/Run00122818_event16944987_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122818          at (nside,pix)=(16,1252) [llh=1054.73]: dec=9.59deg RA=25.31deg / 1.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122818_Subrun00000000_00000045_event16944987.i3.zst -n Run00122818 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1252,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122818   -o /mnt/output_files/Run00122818_event16944987_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122818          at (nside,pix)=(128,82214) [llh=1022.05]: dec=9.29deg RA=26.72deg / 1.78hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122818_Subrun00000000_00000045_event16944987.i3.zst -n Run00122818 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,82214,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122818   -o /mnt/output_files/Run00122818_event16944987_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122818          at (nside,pix)=(1024,5282094) [llh=1021.35]: dec=9.22deg RA=26.59deg / 1.77hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122818_event16944987_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122895_Subrun00000000_00000185_event69011827.i3.zst -n Run00122895 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122895   -o /mnt/output_files/Run00122895_event69011827_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122895          at (nside,pix)=(16,1520) [llh=1759.69]: dec=0.00deg RA=92.81deg / 6.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122895_Subrun00000000_00000185_event69011827.i3.zst -n Run00122895 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1520,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122895   -o /mnt/output_files/Run00122895_event69011827_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122895          at (nside,pix)=(128,97153) [llh=1682.29]: dec=0.60deg RA=91.05deg / 6.07hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122895_Subrun00000000_00000185_event69011827.i3.zst -n Run00122895 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,97153,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122895   -o /mnt/output_files/Run00122895_event69011827_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122895          at (nside,pix)=(1024,6229007) [llh=1679.64]: dec=0.56deg RA=91.32deg / 6.09hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122895_event69011827_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122973_Subrun00000000_00000017_event6578595.i3.zst  -n Run00122973 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00122973   -o /mnt/output_files/Run00122973_event6578595_scanned16.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122973          at (nside,pix)=(16,1847) [llh=9940.21]: dec=-12.02deg RA=129.38deg / 8.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122973_Subrun00000000_00000017_event6578595.i3.zst  -n Run00122973 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1847,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00122973   -o /mnt/output_files/Run00122973_event6578595_scanned128.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122973          at (nside,pix)=(128,116153) [llh=9001.40]: dec=-10.50deg RA=130.08deg / 8.67hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00122973_Subrun00000000_00000017_event6578595.i3.zst  -n Run00122973 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,116153,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00122973   -o /mnt/output_files/Run00122973_event6578595_scanned1024.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00122973          at (nside,pix)=(1024,7441865) [llh=8996.79]: dec=-10.54deg RA=130.17deg / 8.68hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00122973_event6578595_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123107_Subrun00000000_00000022_event8144529.i3.zst  -n Run00123107 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123107   -o /mnt/output_files/Run00123107_event8144529_scanned16.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123107          at (nside,pix)=(16,1253) [llh=1586.40]: dec=9.59deg RA=30.94deg / 2.06hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123107_Subrun00000000_00000022_event8144529.i3.zst  -n Run00123107 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1253,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123107   -o /mnt/output_files/Run00123107_event8144529_scanned128.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123107          at (nside,pix)=(128,80686) [llh=1400.57]: dec=10.20deg RA=32.70deg / 2.18hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123107_Subrun00000000_00000022_event8144529.i3.zst  -n Run00123107 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,80686,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123107   -o /mnt/output_files/Run00123107_event8144529_scanned1024.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123107          at (nside,pix)=(1024,5167478) [llh=1394.82]: dec=10.28deg RA=32.92deg / 2.19hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123107_event8144529_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123145_Subrun00000000_00000094_event34573112.i3.zst -n Run00123145 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123145   -o /mnt/output_files/Run00123145_event34573112_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123145          at (nside,pix)=(16,1301) [llh=3074.64]: dec=9.59deg RA=300.94deg / 20.06hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123145_Subrun00000000_00000094_event34573112.i3.zst -n Run00123145 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1301,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123145   -o /mnt/output_files/Run00123145_event34573112_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123145          at (nside,pix)=(128,79021) [llh=2968.61]: dec=11.42deg RA=301.99deg / 20.13hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123145_Subrun00000000_00000094_event34573112.i3.zst -n Run00123145 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,79021,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123145   -o /mnt/output_files/Run00123145_event34573112_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123145          at (nside,pix)=(1024,5027179) [llh=2967.77]: dec=11.61deg RA=301.90deg / 20.13hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123145_event34573112_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123228_Subrun00000000_00000110_event40504010.i3.zst -n Run00123228 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123228   -o /mnt/output_files/Run00123228_event40504010_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123228          at (nside,pix)=(16,540) [llh=2309.55]: dec=41.81deg RA=340.31deg / 22.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123228_Subrun00000000_00000110_event40504010.i3.zst -n Run00123228 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,540,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123228   -o /mnt/output_files/Run00123228_event40504010_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123228          at (nside,pix)=(128,32999) [llh=2210.29]: dec=41.81deg RA=342.77deg / 22.85hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123228_Subrun00000000_00000110_event40504010.i3.zst -n Run00123228 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,32999,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123228   -o /mnt/output_files/Run00123228_event40504010_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123228          at (nside,pix)=(128,32999) [llh=2210.29]: dec=41.81deg RA=342.77deg / 22.85hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123228_event40504010_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123240_Subrun00000000_00000135_event49730417.i3.zst -n Run00123240 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123240   -o /mnt/output_files/Run00123240_event49730417_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123240          at (nside,pix)=(16,1975) [llh=15149.58]: dec=-16.96deg RA=129.38deg / 8.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123240_Subrun00000000_00000135_event49730417.i3.zst -n Run00123240 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1975,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123240   -o /mnt/output_files/Run00123240_event49730417_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123240          at (nside,pix)=(128,127416) [llh=14995.28]: dec=-17.27deg RA=129.38deg / 8.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123240_Subrun00000000_00000135_event49730417.i3.zst -n Run00123240 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,127416,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123240   -o /mnt/output_files/Run00123240_event49730417_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123240          at (nside,pix)=(1024,8158654) [llh=14987.50]: dec=-17.27deg RA=129.24deg / 8.62hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123240_event49730417_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123281_Subrun00000000_00000142_event52248792.i3.zst -n Run00123281 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123281   -o /mnt/output_files/Run00123281_event52248792_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123281          at (nside,pix)=(16,1042) [llh=1559.27]: dec=19.47deg RA=284.06deg / 18.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123281_Subrun00000000_00000142_event52248792.i3.zst -n Run00123281 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1042,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123281   -o /mnt/output_files/Run00123281_event52248792_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123281          at (nside,pix)=(128,65685) [llh=1540.27]: dec=19.47deg RA=285.12deg / 19.01hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123281_Subrun00000000_00000142_event52248792.i3.zst -n Run00123281 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,65685,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123281   -o /mnt/output_files/Run00123281_event52248792_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123281          at (nside,pix)=(1024,4195500) [llh=1540.02]: dec=19.47deg RA=285.16deg / 19.01hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123281_event52248792_scanned128.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123334_Subrun00000000_00000205_event75182550.i3.zst -n Run00123334 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123334   -o /mnt/output_files/Run00123334_event75182550_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123334          at (nside,pix)=(16,1939) [llh=4299.76]: dec=-14.48deg RA=289.69deg / 19.31hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123334_Subrun00000000_00000205_event75182550.i3.zst -n Run00123334 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1939,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123334   -o /mnt/output_files/Run00123334_event75182550_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123334          at (nside,pix)=(128,122523) [llh=4279.28]: dec=-14.17deg RA=288.98deg / 19.27hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123334_Subrun00000000_00000205_event75182550.i3.zst -n Run00123334 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,122523,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123334   -o /mnt/output_files/Run00123334_event75182550_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123334          at (nside,pix)=(1024,7836888) [llh=4279.19]: dec=-14.21deg RA=288.98deg / 19.27hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123334_event75182550_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123620_Subrun00000000_00000129_event47444787.i3.zst -n Run00123620 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123620   -o /mnt/output_files/Run00123620_event47444787_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123620          at (nside,pix)=(16,1602) [llh=1216.19]: dec=-2.39deg RA=191.25deg / 12.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123620_Subrun00000000_00000129_event47444787.i3.zst -n Run00123620 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1602,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123620   -o /mnt/output_files/Run00123620_event47444787_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123620          at (nside,pix)=(128,102929) [llh=1209.04]: dec=-2.69deg RA=191.95deg / 12.80hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123620_Subrun00000000_00000129_event47444787.i3.zst -n Run00123620 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,102929,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123620   -o /mnt/output_files/Run00123620_event47444787_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123620          at (nside,pix)=(1024,6586507) [llh=1208.55]: dec=-2.69deg RA=192.26deg / 12.82hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123620_event47444787_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123662_Subrun00000000_00000075_event27529428.i3.zst -n Run00123662 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123662   -o /mnt/output_files/Run00123662_event27529428_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123662          at (nside,pix)=(16,25) [llh=813.07]: dec=78.28deg RA=33.75deg / 2.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123662_Subrun00000000_00000075_event27529428.i3.zst -n Run00123662 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,25,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123662   -o /mnt/output_files/Run00123662_event27529428_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123662          at (nside,pix)=(128,1752) [llh=811.11]: dec=79.02deg RA=37.50deg / 2.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123662_Subrun00000000_00000075_event27529428.i3.zst -n Run00123662 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,1752,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123662   -o /mnt/output_files/Run00123662_event27529428_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123662          at (nside,pix)=(1024,115781) [llh=810.96]: dec=78.97deg RA=37.90deg / 2.53hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123662_event27529428_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123751_Subrun00000000_00000093_event34239163.i3.zst -n Run00123751 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123751   -o /mnt/output_files/Run00123751_event34239163_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123751          at (nside,pix)=(16,1565) [llh=4958.52]: dec=0.00deg RA=345.94deg / 23.06hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123751_Subrun00000000_00000093_event34239163.i3.zst -n Run00123751 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1565,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123751   -o /mnt/output_files/Run00123751_event34239163_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123751          at (nside,pix)=(128,95978) [llh=4682.35]: dec=1.49deg RA=344.53deg / 22.97hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123751_Subrun00000000_00000093_event34239163.i3.zst -n Run00123751 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,95978,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123751   -o /mnt/output_files/Run00123751_event34239163_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123751          at (nside,pix)=(1024,6121297) [llh=4672.80]: dec=1.57deg RA=344.66deg / 22.98hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123751_event34239163_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123762_Subrun00000000_00000197_event72626160.i3.zst -n Run00123762 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123762   -o /mnt/output_files/Run00123762_event72626160_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123762          at (nside,pix)=(16,724) [llh=3923.21]: dec=32.80deg RA=292.50deg / 19.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123762_Subrun00000000_00000197_event72626160.i3.zst -n Run00123762 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,724,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123762   -o /mnt/output_files/Run00123762_event72626160_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123762          at (nside,pix)=(128,44705) [llh=3913.55]: dec=33.15deg RA=293.20deg / 19.55hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123762_Subrun00000000_00000197_event72626160.i3.zst -n Run00123762 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,44705,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123762   -o /mnt/output_files/Run00123762_event72626160_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123762          at (nside,pix)=(1024,2864391) [llh=3911.07]: dec=33.02deg RA=293.12deg / 19.54hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123762_event72626160_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123867_Subrun00000000_00000031_event11659459.i3.zst -n Run00123867 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123867   -o /mnt/output_files/Run00123867_event11659459_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123867          at (nside,pix)=(16,1500) [llh=2959.25]: dec=2.39deg RA=337.50deg / 22.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123867_Subrun00000000_00000031_event11659459.i3.zst -n Run00123867 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1500,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123867   -o /mnt/output_files/Run00123867_event11659459_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
 ** best entry for Run00123867          at (nside,pix)=(128,96992) [llh=2858.94]: dec=0.90deg RA=337.50deg / 22.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123867_Subrun00000000_00000031_event11659459.i3.zst -n Run00123867 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,96992,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123867   -o /mnt/output_files/Run00123867_event11659459_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123867          at (nside,pix)=(1024,6215425) [llh=2857.59]: dec=0.71deg RA=337.59deg / 22.51hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123867_event11659459_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123986_Subrun00000000_00000173_event63557286.i3.zst -n Run00123986_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123986_0 -o /mnt/output_files/Run00123986_event63557286_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123986_0        at (nside,pix)=(16,569) [llh=773.96]: dec=38.68deg RA=140.62deg / 9.38hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123986_Subrun00000000_00000173_event63557286.i3.zst -n Run00123986_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,569,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123986_0 -o /mnt/output_files/Run00123986_event63557286_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123986_0        at (nside,pix)=(128,38341) [llh=750.78]: dec=37.54deg RA=138.52deg / 9.23hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123986_Subrun00000000_00000173_event63557286.i3.zst -n Run00123986_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,38341,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123986_0 -o /mnt/output_files/Run00123986_event63557286_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123986_0        at (nside,pix)=(1024,2465323) [llh=750.19]: dec=37.45deg RA=138.82deg / 9.25hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123986_event63557286_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123986_Subrun00000000_00000212_event77999595.i3.zst -n Run00123986_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00123986_1 -o /mnt/output_files/Run00123986_event77999595_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123986_1        at (nside,pix)=(16,2199) [llh=359.31]: dec=-24.62deg RA=312.19deg / 20.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123986_Subrun00000000_00000212_event77999595.i3.zst -n Run00123986_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,2199,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00123986_1 -o /mnt/output_files/Run00123986_event77999595_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123986_1        at (nside,pix)=(128,130737) [llh=347.42]: dec=-19.16deg RA=304.45deg / 20.30hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00123986_Subrun00000000_00000212_event77999595.i3.zst -n Run00123986_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,130737,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00123986_1 -o /mnt/output_files/Run00123986_event77999595_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00123986_1        at (nside,pix)=(1024,8377733) [llh=346.79]: dec=-19.35deg RA=304.19deg / 20.28hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00123986_event77999595_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124136_Subrun00000000_00000041_event15174527.i3.zst -n Run00124136 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124136   -o /mnt/output_files/Run00124136_event15174527_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124136          at (nside,pix)=(16,1950) [llh=2380.78]: dec=-14.48deg RA=351.56deg / 23.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124136_Subrun00000000_00000041_event15174527.i3.zst -n Run00124136 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1950,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124136   -o /mnt/output_files/Run00124136_event15174527_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124136          at (nside,pix)=(128,121585) [llh=2350.70]: dec=-13.55deg RA=349.45deg / 23.30hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124136_Subrun00000000_00000041_event15174527.i3.zst -n Run00124136 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,121585,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124136   -o /mnt/output_files/Run00124136_event15174527_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124136          at (nside,pix)=(1024,7767945) [llh=2350.34]: dec=-13.55deg RA=349.58deg / 23.31hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124136_event15174527_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124221_Subrun00000000_00000208_event76481548.i3.zst -n Run00124221 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124221   -o /mnt/output_files/Run00124221_event76481548_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124221          at (nside,pix)=(16,1220) [llh=746.60]: dec=12.02deg RA=202.50deg / 13.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124221_Subrun00000000_00000208_event76481548.i3.zst -n Run00124221 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1220,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124221   -o /mnt/output_files/Run00124221_event76481548_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124221          at (nside,pix)=(128,76320) [llh=741.40]: dec=12.94deg RA=202.50deg / 13.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124221_Subrun00000000_00000208_event76481548.i3.zst -n Run00124221 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,76320,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124221   -o /mnt/output_files/Run00124221_event76481548_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124221          at (nside,pix)=(1024,4870401) [llh=741.26]: dec=13.06deg RA=202.59deg / 13.51hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124221_event76481548_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124296_Subrun00000000_00000135_event49827757.i3.zst -n Run00124296 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124296   -o /mnt/output_files/Run00124296_event49827757_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124296          at (nside,pix)=(16,693) [llh=837.65]: dec=32.80deg RA=118.13deg / 7.88hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124296_Subrun00000000_00000135_event49827757.i3.zst -n Run00124296 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,693,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124296   -o /mnt/output_files/Run00124296_event49827757_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124296          at (nside,pix)=(128,44968) [llh=837.59]: dec=32.80deg RA=118.48deg / 7.90hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124296_Subrun00000000_00000135_event49827757.i3.zst -n Run00124296 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,44968,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124296   -o /mnt/output_files/Run00124296_event49827757_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124296          at (nside,pix)=(1024,2903368) [llh=837.52]: dec=32.58deg RA=118.83deg / 7.92hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124296_event49827757_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124340_Subrun00000000_00000052_event19400842.i3.zst -n Run00124340 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124340   -o /mnt/output_files/Run00124340_event19400842_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124340          at (nside,pix)=(16,727) [llh=1653.40]: dec=32.80deg RA=309.38deg / 20.63hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124340_Subrun00000000_00000052_event19400842.i3.zst -n Run00124340 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,727,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124340   -o /mnt/output_files/Run00124340_event19400842_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124340          at (nside,pix)=(128,44725) [llh=1643.55]: dec=33.15deg RA=307.27deg / 20.48hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124340_Subrun00000000_00000052_event19400842.i3.zst -n Run00124340 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,44725,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124340   -o /mnt/output_files/Run00124340_event19400842_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124340          at (nside,pix)=(1024,2872753) [llh=1642.58]: dec=32.93deg RA=308.06deg / 20.54hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124340_event19400842_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124463_Subrun00000000_00000096_event35466777.i3.zst -n Run00124463 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124463   -o /mnt/output_files/Run00124463_event35466777_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124463          at (nside,pix)=(16,344) [llh=744.86]: dec=51.26deg RA=225.00deg / 15.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124463_Subrun00000000_00000096_event35466777.i3.zst -n Run00124463 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,344,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124463   -o /mnt/output_files/Run00124463_event35466777_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124463          at (nside,pix)=(128,22103) [llh=743.99]: dec=50.87deg RA=225.86deg / 15.06hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124463_Subrun00000000_00000096_event35466777.i3.zst -n Run00124463 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,22103,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124463   -o /mnt/output_files/Run00124463_event35466777_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124463          at (nside,pix)=(1024,1398216) [llh=743.87]: dec=51.06deg RA=225.70deg / 15.05hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124463_event35466777_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124547_Subrun00000000_00000178_event66087371.i3.zst -n Run00124547 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124547   -o /mnt/output_files/Run00124547_event66087371_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124547          at (nside,pix)=(16,12) [llh=1230.57]: dec=81.22deg RA=15.00deg / 1.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124547_Subrun00000000_00000178_event66087371.i3.zst -n Run00124547 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,12,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124547   -o /mnt/output_files/Run00124547_event66087371_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124547          at (nside,pix)=(128,1104) [llh=1228.61]: dec=81.22deg RA=1.87deg / 0.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124547_Subrun00000000_00000178_event66087371.i3.zst -n Run00124547 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,1104,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124547   -o /mnt/output_files/Run00124547_event66087371_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124547          at (nside,pix)=(1024,73348) [llh=1228.12]: dec=81.22deg RA=2.11deg / 0.14hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124547_event66087371_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124569_Subrun00000000_00000059_event22040903.i3.zst -n Run00124569 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124569   -o /mnt/output_files/Run00124569_event22040903_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124569          at (nside,pix)=(16,1082) [llh=878.69]: dec=16.96deg RA=146.25deg / 9.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124569_Subrun00000000_00000059_event22040903.i3.zst -n Run00124569 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1082,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124569   -o /mnt/output_files/Run00124569_event22040903_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124569          at (nside,pix)=(128,71121) [llh=873.75]: dec=16.02deg RA=146.95deg / 9.80hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124569_Subrun00000000_00000059_event22040903.i3.zst -n Run00124569 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,71121,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124569   -o /mnt/output_files/Run00124569_event22040903_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124569          at (nside,pix)=(1024,4566664) [llh=873.70]: dec=15.91deg RA=146.95deg / 9.80hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124569_event22040903_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124643_Subrun00000000_00000013_event5182926.i3.zst  -n Run00124643 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124643   -o /mnt/output_files/Run00124643_event5182926_scanned16.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124643          at (nside,pix)=(16,1057) [llh=1473.97]: dec=16.96deg RA=5.62deg / 0.38hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124643_Subrun00000000_00000013_event5182926.i3.zst  -n Run00124643 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1057,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124643   -o /mnt/output_files/Run00124643_event5182926_scanned128.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124643          at (nside,pix)=(128,69897) [llh=1472.85]: dec=16.65deg RA=6.33deg / 0.42hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124643_Subrun00000000_00000013_event5182926.i3.zst  -n Run00124643 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,69897,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124643   -o /mnt/output_files/Run00124643_event5182926_scanned1024.i3.zst  --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124643          at (nside,pix)=(1024,4495431) [llh=1472.69]: dec=16.57deg RA=6.28deg / 0.42hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124643_event5182926_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124693_Subrun00000000_00000088_event33063779.i3.zst -n Run00124693 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124693   -o /mnt/output_files/Run00124693_event33063779_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124693          at (nside,pix)=(16,389) [llh=567.37]: dec=48.14deg RA=163.93deg / 10.93hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124693_Subrun00000000_00000088_event33063779.i3.zst -n Run00124693 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,389,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124693   -o /mnt/output_files/Run00124693_event33063779_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124693          at (nside,pix)=(128,26889) [llh=563.78]: dec=46.57deg RA=162.54deg / 10.84hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2013_data_Run00124693_Subrun00000000_00000088_event33063779.i3.zst -n Run00124693 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,26889,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124693   -o /mnt/output_files/Run00124693_event33063779_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124693          at (nside,pix)=(1024,1722185) [llh=563.51]: dec=46.57deg RA=162.30deg / 10.82hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124693_event33063779_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124829_Subrun00000000_00000193_event42577032.i3.zst -n Run00124829   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124829   -o /mnt/output_files/Run00124829_event42577032_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124829          at (nside,pix)=(16,1314) [llh=2822.63]: dec=7.18deg RA=11.25deg / 0.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124829_Subrun00000000_00000193_event42577032.i3.zst -n Run00124829   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1314,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124829   -o /mnt/output_files/Run00124829_event42577032_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124829          at (nside,pix)=(128,85262) [llh=2700.48]: dec=7.48deg RA=9.84deg / 0.66hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124829_Subrun00000000_00000193_event42577032.i3.zst -n Run00124829   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,85262,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124829   -o /mnt/output_files/Run00124829_event42577032_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124829          at (nside,pix)=(1024,5462126) [llh=2697.07]: dec=7.56deg RA=9.71deg / 0.65hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124829_event42577032_scanned1024.i3.zst
CHECK!
  
####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124852_Subrun00000000_00000339_event74171655.i3.zst -n Run00124852   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124852   -o /mnt/output_files/Run00124852_event74171655_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124852          at (nside,pix)=(16,1459) [llh=809.93]: dec=2.39deg RA=106.87deg / 7.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124852_Subrun00000000_00000339_event74171655.i3.zst -n Run00124852   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1459,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124852   -o /mnt/output_files/Run00124852_event74171655_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124852          at (nside,pix)=(128,96151) [llh=775.29]: dec=1.19deg RA=106.52deg / 7.10hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124852_Subrun00000000_00000339_event74171655.i3.zst -n Run00124852   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,96151,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124852   -o /mnt/output_files/Run00124852_event74171655_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124852          at (nside,pix)=(1024,6147257) [llh=774.30]: dec=1.31deg RA=106.26deg / 7.08hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124852_event74171655_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124861_Subrun00000000_00000150_event32863663.i3.zst -n Run00124861   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124861   -o /mnt/output_files/Run00124861_event32863663_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124861          at (nside,pix)=(16,1204) [llh=12924.64]: dec=12.02deg RA=112.50deg / 7.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124861_Subrun00000000_00000150_event32863663.i3.zst -n Run00124861   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1204,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124861   -o /mnt/output_files/Run00124861_event32863663_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124861          at (nside,pix)=(128,78749) [llh=12201.27]: dec=11.42deg RA=110.74deg / 7.38hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124861_Subrun00000000_00000150_event32863663.i3.zst -n Run00124861   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,78749,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124861   -o /mnt/output_files/Run00124861_event32863663_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124861          at (nside,pix)=(1024,5041387) [llh=12199.33]: dec=11.45deg RA=110.65deg / 7.38hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124861_event32863663_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124994_Subrun00000000_00000069_event15096469.i3.zst -n Run00124994   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00124994   -o /mnt/output_files/Run00124994_event15096469_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124994          at (nside,pix)=(16,334) [llh=2491.31]: dec=51.26deg RA=155.77deg / 10.38hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124994_Subrun00000000_00000069_event15096469.i3.zst -n Run00124994   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,334,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00124994   -o /mnt/output_files/Run00124994_event15096469_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124994          at (nside,pix)=(128,19183) [llh=2473.94]: dec=53.57deg RA=157.50deg / 10.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00124994_Subrun00000000_00000069_event15096469.i3.zst -n Run00124994   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,19183,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00124994   -o /mnt/output_files/Run00124994_event15096469_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00124994          at (nside,pix)=(1024,1225978) [llh=2473.43]: dec=53.62deg RA=157.07deg / 10.47hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00124994_event15096469_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125001_Subrun00000000_00000335_event73159253.i3.zst -n Run00125001   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125001   -o /mnt/output_files/Run00125001_event73159253_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125001          at (nside,pix)=(16,1444) [llh=1088.36]: dec=2.39deg RA=22.50deg / 1.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125001_Subrun00000000_00000335_event73159253.i3.zst -n Run00125001   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1444,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125001   -o /mnt/output_files/Run00125001_event73159253_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125001          at (nside,pix)=(128,93988) [llh=1044.54]: dec=2.39deg RA=25.66deg / 1.71hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125001_Subrun00000000_00000335_event73159253.i3.zst -n Run00125001   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,93988,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125001   -o /mnt/output_files/Run00125001_event73159253_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125001          at (nside,pix)=(1024,6011174) [llh=1044.29]: dec=2.54deg RA=25.88deg / 1.73hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125001_event73159253_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125011_Subrun00000000_00000198_event43302321.i3.zst -n Run00125011   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125011   -o /mnt/output_files/Run00125011_event43302321_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125011          at (nside,pix)=(16,1162) [llh=1545.70]: dec=14.48deg RA=239.06deg / 15.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125011_Subrun00000000_00000198_event43302321.i3.zst -n Run00125011   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1162,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125011   -o /mnt/output_files/Run00125011_event43302321_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125011          at (nside,pix)=(128,74327) [llh=1518.26]: dec=14.17deg RA=241.17deg / 16.08hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125011_Subrun00000000_00000198_event43302321.i3.zst -n Run00125011   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,74327,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125011   -o /mnt/output_files/Run00125011_event43302321_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125011          at (nside,pix)=(1024,4752052) [llh=1517.85]: dec=14.17deg RA=240.86deg / 16.06hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125011_event43302321_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125046_Subrun00000000_00000296_event64570437.i3.zst -n Run00125046   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125046   -o /mnt/output_files/Run00125046_event64570437_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125046          at (nside,pix)=(16,1056) [llh=1556.81]: dec=16.96deg RA=0.00deg / 0.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125046_Subrun00000000_00000296_event64570437.i3.zst -n Run00125046   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1056,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125046   -o /mnt/output_files/Run00125046_event64570437_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125046          at (nside,pix)=(128,71425) [llh=1462.02]: dec=15.71deg RA=1.05deg / 0.07hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125046_Subrun00000000_00000296_event64570437.i3.zst -n Run00125046   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,71425,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125046   -o /mnt/output_files/Run00125046_event64570437_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125046          at (nside,pix)=(1024,4597769) [llh=1460.26]: dec=15.60deg RA=0.79deg / 0.05hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125046_event64570437_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125071_Subrun00000000_00000143_event31397276.i3.zst -n Run00125071   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125071   -o /mnt/output_files/Run00125071_event31397276_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125071          at (nside,pix)=(16,2354) [llh=2556.97]: dec=-32.80deg RA=101.25deg / 6.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125071_Subrun00000000_00000143_event31397276.i3.zst -n Run00125071   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,2354,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125071   -o /mnt/output_files/Run00125071_event31397276_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125071          at (nside,pix)=(128,151953) [llh=2556.79]: dec=-33.15deg RA=101.95deg / 6.80hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125071_Subrun00000000_00000143_event31397276.i3.zst -n Run00125071   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,151953,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125071   -o /mnt/output_files/Run00125071_event31397276_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125071          at (nside,pix)=(1024,9706630) [llh=2556.67]: dec=-32.89deg RA=101.82deg / 6.79hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125071_event31397276_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125205_Subrun00000000_00000089_event19617837.i3.zst -n Run00125205   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125205   -o /mnt/output_files/Run00125205_event19617837_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125205          at (nside,pix)=(16,1488) [llh=1149.84]: dec=2.39deg RA=270.00deg / 18.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125205_Subrun00000000_00000089_event19617837.i3.zst -n Run00125205   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1488,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125205   -o /mnt/output_files/Run00125205_event19617837_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125205          at (nside,pix)=(128,95362) [llh=1118.61]: dec=1.79deg RA=271.76deg / 18.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125205_Subrun00000000_00000089_event19617837.i3.zst -n Run00125205   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,95362,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125205   -o /mnt/output_files/Run00125205_event19617837_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125205          at (nside,pix)=(1024,6087696) [llh=1117.97]: dec=1.87deg RA=271.45deg / 18.10hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125205_event19617837_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125338_Subrun00000000_00000299_event65606123.i3.zst -n Run00125338   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125338   -o /mnt/output_files/Run00125338_event65606123_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125338          at (nside,pix)=(16,1598) [llh=3289.28]: dec=-2.39deg RA=168.75deg / 11.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125338_Subrun00000000_00000299_event65606123.i3.zst -n Run00125338   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1598,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125338   -o /mnt/output_files/Run00125338_event65606123_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125338          at (nside,pix)=(128,100849) [llh=3127.92]: dec=-1.49deg RA=169.45deg / 11.30hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125338_Subrun00000000_00000299_event65606123.i3.zst -n Run00125338   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,100849,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125338   -o /mnt/output_files/Run00125338_event65606123_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125338          at (nside,pix)=(1024,6467467) [llh=3123.34]: dec=-1.60deg RA=169.72deg / 11.31hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125338_event65606123_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125349_Subrun00000000_00000056_event12316485.i3.zst -n Run00125349   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125349   -o /mnt/output_files/Run00125349_event12316485_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125349          at (nside,pix)=(16,1512) [llh=672.65]: dec=0.00deg RA=47.81deg / 3.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125349_Subrun00000000_00000056_event12316485.i3.zst -n Run00125349   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1512,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125349   -o /mnt/output_files/Run00125349_event12316485_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125349          at (nside,pix)=(128,99144) [llh=655.94]: dec=-0.60deg RA=50.98deg / 3.40hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125349_Subrun00000000_00000056_event12316485.i3.zst -n Run00125349   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,99144,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125349   -o /mnt/output_files/Run00125349_event12316485_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125349          at (nside,pix)=(1024,6359619) [llh=655.79]: dec=-0.63deg RA=50.89deg / 3.39hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125349_event12316485_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125422_Subrun00000000_00000122_event26630854.i3.zst -n Run00125422   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125422   -o /mnt/output_files/Run00125422_event26630854_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125422          at (nside,pix)=(16,1451) [llh=1994.42]: dec=2.39deg RA=61.87deg / 4.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125422_Subrun00000000_00000122_event26630854.i3.zst -n Run00125422   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1451,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125422   -o /mnt/output_files/Run00125422_event26630854_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125422          at (nside,pix)=(128,92507) [llh=1901.97]: dec=3.28deg RA=63.98deg / 4.27hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125422_Subrun00000000_00000122_event26630854.i3.zst -n Run00125422   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,92507,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125422   -o /mnt/output_files/Run00125422_event26630854_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125422          at (nside,pix)=(1024,5937878) [llh=1901.23]: dec=3.21deg RA=63.85deg / 4.26hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125422_event26630854_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125544_Subrun00000000_00000246_event54236696.i3.zst -n Run00125544   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125544   -o /mnt/output_files/Run00125544_event54236696_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125544          at (nside,pix)=(16,1357) [llh=2133.88]: dec=7.18deg RA=253.13deg / 16.88hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125544_Subrun00000000_00000246_event54236696.i3.zst -n Run00125544   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1357,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125544   -o /mnt/output_files/Run00125544_event54236696_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125544          at (nside,pix)=(128,87144) [llh=2094.72]: dec=6.58deg RA=253.48deg / 16.90hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125544_Subrun00000000_00000246_event54236696.i3.zst -n Run00125544   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,87144,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125544   -o /mnt/output_files/Run00125544_event54236696_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125544          at (nside,pix)=(1024,5587779) [llh=2093.58]: dec=6.43deg RA=253.43deg / 16.90hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125544_event54236696_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125558_Subrun00000000_00000087_event19184163.i3.zst -n Run00125558   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125558   -o /mnt/output_files/Run00125558_event19184163_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125558          at (nside,pix)=(16,839) [llh=1207.98]: dec=27.28deg RA=219.37deg / 14.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125558_Subrun00000000_00000087_event19184163.i3.zst -n Run00125558   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,839,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125558   -o /mnt/output_files/Run00125558_event19184163_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125558          at (nside,pix)=(128,52282) [llh=1179.37]: dec=27.95deg RA=221.13deg / 14.74hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125558_Subrun00000000_00000087_event19184163.i3.zst -n Run00125558   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,52282,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125558   -o /mnt/output_files/Run00125558_event19184163_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125558          at (nside,pix)=(1024,3338712) [llh=1178.95]: dec=28.00deg RA=221.48deg / 14.77hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125558_event19184163_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125693_Subrun00000000_00000096_event21174828.i3.zst -n Run00125693   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125693   -o /mnt/output_files/Run00125693_event21174828_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125693          at (nside,pix)=(16,1100) [llh=2190.98]: dec=16.96deg RA=247.50deg / 16.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125693_Subrun00000000_00000096_event21174828.i3.zst -n Run00125693   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1100,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125693   -o /mnt/output_files/Run00125693_event21174828_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125693          at (nside,pix)=(128,69215) [llh=2178.81]: dec=17.27deg RA=246.80deg / 16.45hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125693_Subrun00000000_00000096_event21174828.i3.zst -n Run00125693   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,69215,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125693   -o /mnt/output_files/Run00125693_event21174828_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125693          at (nside,pix)=(1024,4428531) [llh=2177.77]: dec=17.23deg RA=246.36deg / 16.42hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125693_event21174828_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125709_Subrun00000000_00000028_event6405911.i3.zst  -n Run00125709   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125709   -o /mnt/output_files/Run00125709_event6405911_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125709          at (nside,pix)=(16,1560) [llh=1217.90]: dec=0.00deg RA=317.81deg / 21.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125709_Subrun00000000_00000028_event6405911.i3.zst  -n Run00125709   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1560,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125709   -o /mnt/output_files/Run00125709_event6405911_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125709          at (nside,pix)=(128,95428) [llh=1189.39]: dec=1.79deg RA=318.16deg / 21.21hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125709_Subrun00000000_00000028_event6405911.i3.zst  -n Run00125709   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,95428,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125709   -o /mnt/output_files/Run00125709_event6405911_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125709          at (nside,pix)=(1024,6120995) [llh=1189.00]: dec=1.57deg RA=318.12deg / 21.21hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125709_event6405911_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125757_Subrun00000000_00000058_event12938244.i3.zst -n Run00125757   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125757   -o /mnt/output_files/Run00125757_event12938244_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125757          at (nside,pix)=(16,1600) [llh=1412.62]: dec=-2.39deg RA=180.00deg / 12.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125757_Subrun00000000_00000058_event12938244.i3.zst -n Run00125757   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1600,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125757   -o /mnt/output_files/Run00125757_event12938244_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125757          at (nside,pix)=(128,101374) [llh=1369.71]: dec=-1.79deg RA=178.95deg / 11.93hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125757_Subrun00000000_00000058_event12938244.i3.zst -n Run00125757   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,101374,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125757   -o /mnt/output_files/Run00125757_event12938244_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125757          at (nside,pix)=(1024,6504437) [llh=1367.98]: dec=-1.94deg RA=179.08deg / 11.94hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125757_event12938244_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125796_Subrun00000000_00000072_event16042897.i3.zst -n Run00125796   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125796   -o /mnt/output_files/Run00125796_event16042897_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125796          at (nside,pix)=(16,1497) [llh=951.96]: dec=2.39deg RA=320.62deg / 21.38hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125796_Subrun00000000_00000072_event16042897.i3.zst -n Run00125796   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1497,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125796   -o /mnt/output_files/Run00125796_event16042897_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125796          at (nside,pix)=(128,93381) [llh=907.87]: dec=2.99deg RA=318.87deg / 21.26hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125796_Subrun00000000_00000072_event16042897.i3.zst -n Run00125796   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,93381,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125796   -o /mnt/output_files/Run00125796_event16042897_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125796          at (nside,pix)=(1024,5973546) [llh=904.19]: dec=2.91deg RA=318.74deg / 21.25hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125796_event16042897_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125800_Subrun00000000_00000376_event83097666.i3.zst -n Run00125800   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125800   -o /mnt/output_files/Run00125800_event83097666_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125800          at (nside,pix)=(16,784) [llh=2115.74]: dec=30.00deg RA=272.81deg / 18.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125800_Subrun00000000_00000376_event83097666.i3.zst -n Run00125800   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,784,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125800   -o /mnt/output_files/Run00125800_event83097666_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125800          at (nside,pix)=(128,50819) [llh=2105.32]: dec=28.97deg RA=272.11deg / 18.14hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125800_Subrun00000000_00000376_event83097666.i3.zst -n Run00125800   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,50819,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125800   -o /mnt/output_files/Run00125800_event83097666_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125800          at (nside,pix)=(1024,3265560) [llh=2105.16]: dec=28.76deg RA=272.11deg / 18.14hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125800_event83097666_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125929_Subrun00000000_00000050_event11025256.i3.zst -n Run00125929   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125929   -o /mnt/output_files/Run00125929_event11025256_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125929          at (nside,pix)=(16,1402) [llh=1575.76]: dec=4.78deg RA=149.06deg / 9.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125929_Subrun00000000_00000050_event11025256.i3.zst -n Run00125929   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1402,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125929   -o /mnt/output_files/Run00125929_event11025256_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125929          at (nside,pix)=(128,90585) [llh=1489.94]: dec=4.48deg RA=152.58deg / 10.17hours  
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125929_Subrun00000000_00000050_event11025256.i3.zst -n Run00125929   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,90585,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125929   -o /mnt/output_files/Run00125929_event11025256_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125929          at (nside,pix)=(1024,5816007) [llh=1488.84]: dec=4.33deg RA=152.53deg / 10.17hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125929_event11025256_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125934_Subrun00000000_00000253_event55750717.i3.zst -n Run00125934   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125934   -o /mnt/output_files/Run00125934_event55750717_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125934          at (nside,pix)=(16,1363) [llh=1371.86]: dec=7.18deg RA=286.88deg / 19.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125934_Subrun00000000_00000253_event55750717.i3.zst -n Run00125934   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1363,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125929 -n Run00125934   -o /mnt/output_files/Run00125934_event55750717_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125934          at (nside,pix)=(128,87704) [llh=1332.76]: dec=6.28deg RA=286.88deg / 19.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125934_Subrun00000000_00000253_event55750717.i3.zst -n Run00125934   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,87704,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125929 -n Run00125934   -o /mnt/output_files/Run00125934_event55750717_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125934          at (nside,pix)=(1024,5588160) [llh=1329.70]: dec=6.43deg RA=286.92deg / 19.13hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125934_event55750717_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125940_Subrun00000000_00000033_event7449833.i3.zst  -n Run00125940   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125940   -o /mnt/output_files/Run00125940_event7449833_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125940          at (nside,pix)=(16,1137) [llh=1446.92]: dec=14.48deg RA=98.44deg / 6.56hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125940_Subrun00000000_00000033_event7449833.i3.zst  -n Run00125940   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1137,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125940   -o /mnt/output_files/Run00125940_event7449833_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125940          at (nside,pix)=(128,74120) [llh=1291.35]: dec=14.17deg RA=95.63deg / 6.38hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125940_Subrun00000000_00000033_event7449833.i3.zst  -n Run00125940   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,74120,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125940   -o /mnt/output_files/Run00125940_event7449833_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125940          at (nside,pix)=(1024,4754499) [llh=1290.44]: dec=14.13deg RA=95.89deg / 6.39hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125940_event7449833_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125968_Subrun00000000_00000278_event61389842.i3.zst -n Run00125968   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125968   -o /mnt/output_files/Run00125968_event61389842_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125968          at (nside,pix)=(16,1393) [llh=1361.21]: dec=4.78deg RA=98.44deg / 6.56hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125968_Subrun00000000_00000278_event61389842.i3.zst -n Run00125968   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1393,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125968   -o /mnt/output_files/Run00125968_event61389842_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125968          at (nside,pix)=(128,90511) [llh=1318.93]: dec=4.48deg RA=100.55deg / 6.70hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125968_Subrun00000000_00000278_event61389842.i3.zst -n Run00125968   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,90511,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125968   -o /mnt/output_files/Run00125968_event61389842_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125968          at (nside,pix)=(1024,5786742) [llh=1317.48]: dec=4.59deg RA=100.37deg / 6.69hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125968_event61389842_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125973_Subrun00000000_00000366_event80686964.i3.zst -n Run00125973   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00125973   -o /mnt/output_files/Run00125973_event80686964_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125973          at (nside,pix)=(16,1439) [llh=1149.38]: dec=4.78deg RA=357.19deg / 23.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125973_Subrun00000000_00000366_event80686964.i3.zst -n Run00125973   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1439,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00125973   -o /mnt/output_files/Run00125973_event80686964_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125973          at (nside,pix)=(128,87806) [llh=1141.20]: dec=6.28deg RA=358.59deg / 23.91hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00125973_Subrun00000000_00000366_event80686964.i3.zst -n Run00125973   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,87806,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00125973   -o /mnt/output_files/Run00125973_event80686964_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00125973          at (nside,pix)=(1024,5593071) [llh=1140.15]: dec=6.39deg RA=358.51deg / 23.90hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00125973_event80686964_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126082_Subrun00000000_00000184_event40384770.i3.zst -n Run00126082   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126082   -o /mnt/output_files/Run00126082_event40384770_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126082          at (nside,pix)=(16,249) [llh=836.79]: dec=57.40deg RA=241.36deg / 16.09hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126082_Subrun00000000_00000184_event40384770.i3.zst -n Run00126082   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,249,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126082   -o /mnt/output_files/Run00126082_event40384770_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126082          at (nside,pix)=(128,17732) [llh=824.69]: dec=55.11deg RA=237.93deg / 15.86hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126082_Subrun00000000_00000184_event40384770.i3.zst -n Run00126082   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,17732,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126082   -o /mnt/output_files/Run00126082_event40384770_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126082          at (nside,pix)=(1024,1131490) [llh=824.52]: dec=55.11deg RA=237.75deg / 15.85hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126082_event40384770_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126148_Subrun00000000_00000339_event74589372.i3.zst -n Run00126148   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126148   -o /mnt/output_files/Run00126148_event74589372_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126148          at (nside,pix)=(16,1654) [llh=1631.58]: dec=-4.78deg RA=126.56deg / 8.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126148_Subrun00000000_00000339_event74589372.i3.zst -n Run00126148   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1654,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126148   -o /mnt/output_files/Run00126148_event74589372_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126148          at (nside,pix)=(128,103861) [llh=1500.45]: dec=-3.28deg RA=127.27deg / 8.48hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126148_Subrun00000000_00000339_event74589372.i3.zst -n Run00126148   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,103861,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126148   -o /mnt/output_files/Run00126148_event74589372_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126148          at (nside,pix)=(1024,6659493) [llh=1500.01]: dec=-3.36deg RA=127.05deg / 8.47hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126148_event74589372_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126308_Subrun00000000_00000095_event20883844.i3.zst -n Run00126308   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126308   -o /mnt/output_files/Run00126308_event20883844_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126308          at (nside,pix)=(16,1125) [llh=919.99]: dec=14.48deg RA=30.94deg / 2.06hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126308_Subrun00000000_00000095_event20883844.i3.zst -n Run00126308   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1125,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126308   -o /mnt/output_files/Run00126308_event20883844_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126308          at (nside,pix)=(128,72492) [llh=915.65]: dec=15.09deg RA=31.29deg / 2.09hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126308_Subrun00000000_00000095_event20883844.i3.zst -n Run00126308   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,72492,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126308   -o /mnt/output_files/Run00126308_event20883844_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126308          at (nside,pix)=(1024,4659553) [llh=915.40]: dec=15.02deg RA=31.07deg / 2.07hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126308_event20883844_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126370_Subrun00000000_00000281_event61611641.i3.zst -n Run00126370   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126370   -o /mnt/output_files/Run00126370_event61611641_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126370          at (nside,pix)=(16,1200) [llh=1685.79]: dec=12.02deg RA=90.00deg / 6.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126370_Subrun00000000_00000281_event61611641.i3.zst -n Run00126370   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1200,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126370   -o /mnt/output_files/Run00126370_event61611641_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126370          at (nside,pix)=(128,77186) [llh=1564.35]: dec=12.33deg RA=91.41deg / 6.09hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2014_data_Run00126370_Subrun00000000_00000281_event61611641.i3.zst -n Run00126370   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,77186,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126370   -o /mnt/output_files/Run00126370_event61611641_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126370          at (nside,pix)=(1024,4967441) [llh=1557.38]: dec=12.14deg RA=91.49deg / 6.10hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126370_event61611641_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126405_Subrun00000000_00000138_event50771014.i3.zst -n Run00126405   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126405   -o /mnt/output_files/Run00126405_event50771014_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126405          at (nside,pix)=(16,1593) [llh=1157.40]: dec=-2.39deg RA=140.62deg / 9.38hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126405_Subrun00000000_00000138_event50771014.i3.zst -n Run00126405   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1593,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126405   -o /mnt/output_files/Run00126405_event50771014_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126405          at (nside,pix)=(128,100807) [llh=1131.67]: dec=-1.49deg RA=139.92deg / 9.33hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126405_Subrun00000000_00000138_event50771014.i3.zst -n Run00126405   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,100807,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126405   -o /mnt/output_files/Run00126405_event50771014_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126405          at (nside,pix)=(1024,6454838) [llh=1131.61]: dec=-1.49deg RA=139.79deg / 9.32hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126405_event50771014_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126423_Subrun00000000_00000137_event50123696.i3.zst -n Run00126423   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126423   -o /mnt/output_files/Run00126423_event50123696_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126423          at (nside,pix)=(16,1307) [llh=2148.78]: dec=9.59deg RA=334.69deg / 22.31hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126423_Subrun00000000_00000137_event50123696.i3.zst -n Run00126423   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1307,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126423   -o /mnt/output_files/Run00126423_event50123696_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126423          at (nside,pix)=(128,82138) [llh=2138.61]: dec=9.59deg RA=333.63deg / 22.24hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126423_Subrun00000000_00000137_event50123696.i3.zst -n Run00126423   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,82138,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126423   -o /mnt/output_files/Run00126423_event50123696_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126423          at (nside,pix)=(1024,5240529) [llh=2137.72]: dec=9.63deg RA=333.37deg / 22.22hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126423_event50123696_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126456_Subrun00000000_00000004_event1581608.i3.zst  -n Run00126456_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126456_0 -o /mnt/output_files/Run00126456_event1581608_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126456_0        at (nside,pix)=(16,1512) [llh=2582.21]: dec=0.00deg RA=47.81deg / 3.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126456_Subrun00000000_00000004_event1581608.i3.zst  -n Run00126456_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1512,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126456_0 -o /mnt/output_files/Run00126456_event1581608_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126456_0        at (nside,pix)=(128,97606) [llh=2498.13]: dec=0.30deg RA=49.22deg / 3.28hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126456_Subrun00000000_00000004_event1581608.i3.zst  -n Run00126456_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,97606,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126456_0 -o /mnt/output_files/Run00126456_event1581608_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126456_0        at (nside,pix)=(1024,6257203) [llh=2496.57]: dec=0.30deg RA=49.53deg / 3.30hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126456_event1581608_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126456_Subrun00000000_00000098_event35956042.i3.zst -n Run00126456_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126456_1 -o /mnt/output_files/Run00126456_event35956042_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126456_1        at (nside,pix)=(16,1547) [llh=2300.77]: dec=0.00deg RA=244.69deg / 16.31hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126456_Subrun00000000_00000098_event35956042.i3.zst -n Run00126456_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1547,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126456_1 -o /mnt/output_files/Run00126456_event35956042_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126456_1        at (nside,pix)=(128,97885) [llh=2281.19]: dec=0.30deg RA=245.39deg / 16.36hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126456_Subrun00000000_00000098_event35956042.i3.zst -n Run00126456_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,97885,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126456_1 -o /mnt/output_files/Run00126456_event35956042_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126456_1        at (nside,pix)=(1024,6267624) [llh=2281.09]: dec=0.22deg RA=245.43deg / 16.36hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126456_event35956042_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126514_Subrun00000000_00000201_event73786337.i3.zst -n Run00126514   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126514   -o /mnt/output_files/Run00126514_event73786337_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126514          at (nside,pix)=(16,1516) [llh=934.25]: dec=0.00deg RA=70.31deg / 4.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126514_Subrun00000000_00000201_event73786337.i3.zst -n Run00126514   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1516,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126514   -o /mnt/output_files/Run00126514_event73786337_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126514          at (nside,pix)=(128,96614) [llh=919.65]: dec=0.90deg RA=71.72deg / 4.78hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126514_Subrun00000000_00000201_event73786337.i3.zst -n Run00126514   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,96614,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126514   -o /mnt/output_files/Run00126514_event73786337_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126514          at (nside,pix)=(1024,6196018) [llh=919.36]: dec=0.86deg RA=71.89deg / 4.79hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126514_event73786337_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126515_Subrun00000000_00000054_event20091930.i3.zst -n Run00126515   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126515   -o /mnt/output_files/Run00126515_event20091930_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126515          at (nside,pix)=(16,1046) [llh=2544.79]: dec=19.47deg RA=306.56deg / 20.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126515_Subrun00000000_00000054_event20091930.i3.zst -n Run00126515   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1046,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126515   -o /mnt/output_files/Run00126515_event20091930_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126515          at (nside,pix)=(128,66228) [llh=2536.18]: dec=19.16deg RA=306.56deg / 20.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126515_Subrun00000000_00000054_event20091930.i3.zst -n Run00126515   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,66228,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126515   -o /mnt/output_files/Run00126515_event20091930_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126515          at (nside,pix)=(1024,4236702) [llh=2535.58]: dec=19.08deg RA=306.43deg / 20.43hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126515_event20091930_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126620_Subrun00000000_00000052_event19175993.i3.zst -n Run00126620   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126620   -o /mnt/output_files/Run00126620_event19175993_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126620          at (nside,pix)=(16,858) [llh=1753.79]: dec=27.28deg RA=326.25deg / 21.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126620_Subrun00000000_00000052_event19175993.i3.zst -n Run00126620   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,858,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126620   -o /mnt/output_files/Run00126620_event19175993_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126620          at (nside,pix)=(128,54992) [llh=1746.98]: dec=26.28deg RA=326.25deg / 21.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126620_Subrun00000000_00000052_event19175993.i3.zst -n Run00126620   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,54992,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126620   -o /mnt/output_files/Run00126620_event19175993_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126620          at (nside,pix)=(1024,3499648) [llh=1746.75]: dec=26.36deg RA=326.29deg / 21.75hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126620_event19175993_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126703_Subrun00000000_00000081_event23477554.i3.zst -n Run00126703   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126703   -o /mnt/output_files/Run00126703_event23477554_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126703          at (nside,pix)=(16,1991) [llh=11022.07]: dec=-16.96deg RA=219.37deg / 14.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126703_Subrun00000000_00000081_event23477554.i3.zst -n Run00126703   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1991,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126703   -o /mnt/output_files/Run00126703_event23477554_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126703          at (nside,pix)=(128,127035) [llh=9767.88]: dec=-16.96deg RA=221.84deg / 14.79hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126703_Subrun00000000_00000081_event23477554.i3.zst -n Run00126703   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,127035,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126703   -o /mnt/output_files/Run00126703_event23477554_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126703          at (nside,pix)=(1024,8147419) [llh=9745.32]: dec=-17.15deg RA=221.75deg / 14.78hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126703_event23477554_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126717_Subrun00000000_00000081_event29833358.i3.zst -n Run00126717   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126717   -o /mnt/output_files/Run00126717_event29833358_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126717          at (nside,pix)=(16,792) [llh=1602.25]: dec=30.00deg RA=317.81deg / 21.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126717_Subrun00000000_00000081_event29833358.i3.zst -n Run00126717   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,792,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126717   -o /mnt/output_files/Run00126717_event29833358_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126717          at (nside,pix)=(16,792) [llh=1602.25]: dec=30.00deg RA=317.81deg / 21.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126717_Subrun00000000_00000081_event29833358.i3.zst -n Run00126717   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 16,792,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126717   -o /mnt/output_files/Run00126717_event29833358_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126717          at (nside,pix)=(1024,3139101) [llh=1602.13]: dec=30.09deg RA=317.59deg / 21.17hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126717_event29833358_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126718_Subrun00000000_00000145_event53509959.i3.zst -n Run00126718   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126718   -o /mnt/output_files/Run00126718_event53509959_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126718          at (nside,pix)=(16,1434) [llh=4331.09]: dec=4.78deg RA=329.06deg / 21.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126718_Subrun00000000_00000145_event53509959.i3.zst -n Run00126718   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1434,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126718   -o /mnt/output_files/Run00126718_event53509959_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126718          at (nside,pix)=(128,87763) [llh=4084.42]: dec=6.28deg RA=328.36deg / 21.89hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126718_Subrun00000000_00000145_event53509959.i3.zst -n Run00126718   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,87763,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126718   -o /mnt/output_files/Run00126718_event53509959_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126718          at (nside,pix)=(1024,5617303) [llh=4082.71]: dec=6.17deg RA=328.27deg / 21.88hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126718_event53509959_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126769_Subrun00000000_00000171_event62990844.i3.zst -n Run00126769   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126769   -o /mnt/output_files/Run00126769_event62990844_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126769          at (nside,pix)=(16,1626) [llh=1151.94]: dec=-2.39deg RA=326.25deg / 21.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126769_Subrun00000000_00000171_event62990844.i3.zst -n Run00126769   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1626,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126769   -o /mnt/output_files/Run00126769_event62990844_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126769          at (nside,pix)=(128,102607) [llh=1151.53]: dec=-2.39deg RA=325.90deg / 21.73hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126769_Subrun00000000_00000171_event62990844.i3.zst -n Run00126769   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,102607,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126769   -o /mnt/output_files/Run00126769_event62990844_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126769          at (nside,pix)=(1024,6551164) [llh=1151.42]: dec=-2.35deg RA=325.90deg / 21.73hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126769_event62990844_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126798_Subrun00000000_00000183_event67205547.i3.zst -n Run00126798   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126798   -o /mnt/output_files/Run00126798_event67205547_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126798          at (nside,pix)=(16,682) [llh=2945.87]: dec=32.80deg RA=56.25deg / 3.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126798_Subrun00000000_00000183_event67205547.i3.zst -n Run00126798   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,682,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126798   -o /mnt/output_files/Run00126798_event67205547_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126798          at (nside,pix)=(128,43342) [llh=2818.08]: dec=33.87deg RA=54.84deg / 3.66hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126798_Subrun00000000_00000183_event67205547.i3.zst -n Run00126798   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,43342,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126798   -o /mnt/output_files/Run00126798_event67205547_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126798          at (nside,pix)=(1024,2771567) [llh=2817.27]: dec=34.00deg RA=54.76deg / 3.65hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126798_event67205547_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126812_Subrun00000000_00000105_event38566267.i3.zst -n Run00126812   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126812   -o /mnt/output_files/Run00126812_event38566267_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126812          at (nside,pix)=(16,824) [llh=2819.34]: dec=27.28deg RA=135.00deg / 9.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126812_Subrun00000000_00000105_event38566267.i3.zst -n Run00126812   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,824,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126812   -o /mnt/output_files/Run00126812_event38566267_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126812          at (nside,pix)=(128,51646) [llh=2590.93]: dec=28.29deg RA=133.59deg / 8.91hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126812_Subrun00000000_00000105_event38566267.i3.zst -n Run00126812   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,51646,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126812   -o /mnt/output_files/Run00126812_event38566267_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126812          at (nside,pix)=(1024,3329522) [llh=2582.73]: dec=28.08deg RA=133.77deg / 8.92hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126812_event38566267_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126848_Subrun00000000_00000024_event8902133.i3.zst  -n Run00126848   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126848   -o /mnt/output_files/Run00126848_event8902133_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126848          at (nside,pix)=(16,758) [llh=1032.60]: dec=30.00deg RA=126.56deg / 8.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126848_Subrun00000000_00000024_event8902133.i3.zst  -n Run00126848   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,758,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126848   -o /mnt/output_files/Run00126848_event8902133_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126848          at (nside,pix)=(128,48568) [llh=985.29]: dec=30.35deg RA=129.38deg / 8.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126848_Subrun00000000_00000024_event8902133.i3.zst  -n Run00126848   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,48568,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126848   -o /mnt/output_files/Run00126848_event8902133_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126848          at (nside,pix)=(1024,3112387) [llh=984.28]: dec=30.35deg RA=129.68deg / 8.65hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126848_event8902133_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126860_Subrun00000000_00000047_event17477746.i3.zst -n Run00126860   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126860   -o /mnt/output_files/Run00126860_event17477746_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126860          at (nside,pix)=(16,1577) [llh=2212.69]: dec=-2.39deg RA=50.62deg / 3.38hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126860_Subrun00000000_00000047_event17477746.i3.zst -n Run00126860   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1577,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126860   -o /mnt/output_files/Run00126860_event17477746_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126860          at (nside,pix)=(128,103238) [llh=2209.95]: dec=-2.99deg RA=49.57deg / 3.30hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126860_Subrun00000000_00000047_event17477746.i3.zst -n Run00126860   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,103238,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126860   -o /mnt/output_files/Run00126860_event17477746_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126860          at (nside,pix)=(1024,6613559) [llh=2209.42]: dec=-2.95deg RA=49.83deg / 3.32hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126860_event17477746_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126863_Subrun00000000_00000038_event14025085.i3.zst -n Run00126863   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126863   -o /mnt/output_files/Run00126863_event14025085_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126863          at (nside,pix)=(16,785) [llh=1249.70]: dec=30.00deg RA=278.44deg / 18.56hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126863_Subrun00000000_00000038_event14025085.i3.zst -n Run00126863   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,785,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126863   -o /mnt/output_files/Run00126863_event14025085_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126863          at (nside,pix)=(128,48782) [llh=1239.49]: dec=30.35deg RA=279.84deg / 18.66hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126863_Subrun00000000_00000038_event14025085.i3.zst -n Run00126863   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,48782,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126863   -o /mnt/output_files/Run00126863_event14025085_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126863          at (nside,pix)=(1024,3114092) [llh=1238.83]: dec=30.35deg RA=279.54deg / 18.64hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126863_event14025085_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126878_Subrun00000000_00000083_event30560694.i3.zst -n Run00126878   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126878   -o /mnt/output_files/Run00126878_event30560694_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126878          at (nside,pix)=(16,1394) [llh=2482.36]: dec=4.78deg RA=104.06deg / 6.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126878_Subrun00000000_00000083_event30560694.i3.zst -n Run00126878   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1394,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126878   -o /mnt/output_files/Run00126878_event30560694_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126878          at (nside,pix)=(128,91539) [llh=2389.77]: dec=3.88deg RA=103.36deg / 6.89hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126878_Subrun00000000_00000083_event30560694.i3.zst -n Run00126878   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,91539,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126878   -o /mnt/output_files/Run00126878_event30560694_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126878          at (nside,pix)=(1024,5856406) [llh=2385.70]: dec=3.96deg RA=103.23deg / 6.88hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126878_event30560694_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126911_Subrun00000000_00000017_event6416344.i3.zst  -n Run00126911   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126911   -o /mnt/output_files/Run00126911_event6416344_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126911          at (nside,pix)=(16,1666) [llh=3026.24]: dec=-4.78deg RA=194.06deg / 12.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126911_Subrun00000000_00000017_event6416344.i3.zst  -n Run00126911   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1666,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126911   -o /mnt/output_files/Run00126911_event6416344_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126911          at (nside,pix)=(128,106516) [llh=3021.43]: dec=-4.78deg RA=194.41deg / 12.96hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126911_Subrun00000000_00000017_event6416344.i3.zst  -n Run00126911   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,106516,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126911   -o /mnt/output_files/Run00126911_event6416344_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126911          at (nside,pix)=(1024,6791333) [llh=3017.99]: dec=-4.56deg RA=194.55deg / 12.97hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126911_event6416344_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126976_Subrun00000000_00000027_event9961785.i3.zst  -n Run00126976   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126976   -o /mnt/output_files/Run00126976_event9961785_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126976          at (nside,pix)=(16,287) [llh=2954.32]: dec=54.34deg RA=176.25deg / 11.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126976_Subrun00000000_00000027_event9961785.i3.zst  -n Run00126976   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,287,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126976   -o /mnt/output_files/Run00126976_event9961785_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126976          at (nside,pix)=(128,20400) [llh=2832.10]: dec=52.42deg RA=178.66deg / 11.91hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126976_Subrun00000000_00000027_event9961785.i3.zst  -n Run00126976   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,20400,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126976   -o /mnt/output_files/Run00126976_event9961785_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126976          at (nside,pix)=(1024,1308950) [llh=2831.80]: dec=52.37deg RA=178.72deg / 11.91hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126976_event9961785_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126989_Subrun00000000_00000162_event59479399.i3.zst -n Run00126989   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00126989   -o /mnt/output_files/Run00126989_event59479399_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126989          at (nside,pix)=(16,963) [llh=1765.03]: dec=22.02deg RA=196.88deg / 13.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126989_Subrun00000000_00000162_event59479399.i3.zst -n Run00126989   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,963,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00126989   -o /mnt/output_files/Run00126989_event59479399_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126989          at (nside,pix)=(128,65049) [llh=1744.83]: dec=19.79deg RA=197.58deg / 13.17hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00126989_Subrun00000000_00000162_event59479399.i3.zst -n Run00126989   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,65049,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00126989   -o /mnt/output_files/Run00126989_event59479399_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00126989          at (nside,pix)=(1024,4145351) [llh=1744.65]: dec=19.95deg RA=197.53deg / 13.17hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00126989_event59479399_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127112_Subrun00000000_00000190_event69211097.i3.zst -n Run00127112   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127112   -o /mnt/output_files/Run00127112_event69211097_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127112          at (nside,pix)=(16,1198) [llh=2143.51]: dec=12.02deg RA=78.75deg / 5.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127112_Subrun00000000_00000190_event69211097.i3.zst -n Run00127112   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1198,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127112   -o /mnt/output_files/Run00127112_event69211097_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127112          at (nside,pix)=(128,76652) [llh=2011.17]: dec=12.64deg RA=76.29deg / 5.09hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127112_Subrun00000000_00000190_event69211097.i3.zst -n Run00127112   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,76652,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127112   -o /mnt/output_files/Run00127112_event69211097_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127112          at (nside,pix)=(1024,4905826) [llh=2010.18]: dec=12.71deg RA=76.16deg / 5.08hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127112_event69211097_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127154_Subrun00000000_00000027_event9907321.i3.zst  -n Run00127154   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127154   -o /mnt/output_files/Run00127154_event9907321_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127154          at (nside,pix)=(16,1615) [llh=4158.31]: dec=-2.39deg RA=264.38deg / 17.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127154_Subrun00000000_00000027_event9907321.i3.zst  -n Run00127154   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1615,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127154   -o /mnt/output_files/Run00127154_event9907321_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127154          at (nside,pix)=(128,102516) [llh=3994.81]: dec=-2.39deg RA=261.91deg / 17.46hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127154_Subrun00000000_00000027_event9907321.i3.zst  -n Run00127154   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,102516,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127154   -o /mnt/output_files/Run00127154_event9907321_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127154          at (nside,pix)=(1024,6538149) [llh=3991.63]: dec=-2.24deg RA=262.05deg / 17.47hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127154_event9907321_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127357_Subrun00000000_00000048_event17650073.i3.zst -n Run00127357   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127357   -o /mnt/output_files/Run00127357_event17650073_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127357          at (nside,pix)=(16,1390) [llh=3056.65]: dec=4.78deg RA=81.56deg / 5.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127357_Subrun00000000_00000048_event17650073.i3.zst -n Run00127357   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1390,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127357   -o /mnt/output_files/Run00127357_event17650073_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127357          at (nside,pix)=(128,89457) [llh=2914.39]: dec=5.08deg RA=79.45deg / 5.30hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127357_Subrun00000000_00000048_event17650073.i3.zst -n Run00127357   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,89457,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127357   -o /mnt/output_files/Run00127357_event17650073_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127357          at (nside,pix)=(1024,5741447) [llh=2913.90]: dec=5.00deg RA=79.41deg / 5.29hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127357_event17650073_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127495_Subrun00000000_00000152_event54505431.i3.zst -n Run00127495   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127495   -o /mnt/output_files/Run00127495_event54505431_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127495          at (nside,pix)=(16,1934) [llh=3754.35]: dec=-14.48deg RA=261.56deg / 17.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127495_Subrun00000000_00000152_event54505431.i3.zst -n Run00127495   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1934,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127495   -o /mnt/output_files/Run00127495_event54505431_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127495          at (nside,pix)=(128,123511) [llh=3698.40]: dec=-14.79deg RA=263.67deg / 17.58hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127495_Subrun00000000_00000152_event54505431.i3.zst -n Run00127495   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,123511,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127495   -o /mnt/output_files/Run00127495_event54505431_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127495          at (nside,pix)=(1024,7910329) [llh=3698.10]: dec=-14.90deg RA=263.76deg / 17.58hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127495_event54505431_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127603_Subrun00000000_00000133_event48070937.i3.zst -n Run00127603   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127603   -o /mnt/output_files/Run00127603_event48070937_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127603          at (nside,pix)=(16,214) [llh=2683.63]: dec=60.43deg RA=310.50deg / 20.70hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127603_Subrun00000000_00000133_event48070937.i3.zst -n Run00127603   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,214,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127603   -o /mnt/output_files/Run00127603_event48070937_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127603          at (nside,pix)=(128,13240) [llh=2642.20]: dec=60.06deg RA=311.67deg / 20.78hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127603_Subrun00000000_00000133_event48070937.i3.zst -n Run00127603   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,13240,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127603   -o /mnt/output_files/Run00127603_event48070937_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127603          at (nside,pix)=(1024,840757) [llh=2641.52]: dec=60.06deg RA=311.88deg / 20.79hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127603_event48070937_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127650_Subrun00000000_00000051_event18431575.i3.zst -n Run00127650   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127650   -o /mnt/output_files/Run00127650_event18431575_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127650          at (nside,pix)=(16,1264) [llh=915.57]: dec=9.59deg RA=92.81deg / 6.19hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127650_Subrun00000000_00000051_event18431575.i3.zst -n Run00127650   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1264,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127650   -o /mnt/output_files/Run00127650_event18431575_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127650          at (nside,pix)=(128,80258) [llh=913.65]: dec=10.50deg RA=91.41deg / 6.09hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127650_Subrun00000000_00000051_event18431575.i3.zst -n Run00127650   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,80258,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127650   -o /mnt/output_files/Run00127650_event18431575_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127650          at (nside,pix)=(1024,5147663) [llh=913.63]: dec=10.47deg RA=91.32deg / 6.09hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127650_event18431575_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127742_Subrun00000000_00000155_event55820225.i3.zst -n Run00127742   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127742   -o /mnt/output_files/Run00127742_event55820225_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127742          at (nside,pix)=(16,1083) [llh=2185.97]: dec=16.96deg RA=151.88deg / 10.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127742_Subrun00000000_00000155_event55820225.i3.zst -n Run00127742   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1083,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127742   -o /mnt/output_files/Run00127742_event55820225_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127742          at (nside,pix)=(128,72151) [llh=2045.41]: dec=15.40deg RA=151.17deg / 10.08hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127742_Subrun00000000_00000155_event55820225.i3.zst -n Run00127742   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,72151,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127742   -o /mnt/output_files/Run00127742_event55820225_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127742          at (nside,pix)=(1024,4611768) [llh=2045.33]: dec=15.48deg RA=151.22deg / 10.08hours 
docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127742_event55820225_scanned1024.i3.zst

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127790_Subrun00000000_00000127_event45902607.i3.zst -n Run00127790   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127790   -o /mnt/output_files/Run00127790_event45902607_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127790          at (nside,pix)=(16,1610) [llh=1901.65]: dec=-2.39deg RA=236.25deg / 15.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127790_Subrun00000000_00000127_event45902607.i3.zst -n Run00127790   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1610,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127790   -o /mnt/output_files/Run00127790_event45902607_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127790          at (nside,pix)=(128,105039) [llh=1844.70]: dec=-3.88deg RA=235.55deg / 15.70hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127790_Subrun00000000_00000127_event45902607.i3.zst -n Run00127790   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,105039,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127790   -o /mnt/output_files/Run00127790_event45902607_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127790          at (nside,pix)=(1024,6738553) [llh=1844.27]: dec=-4.07deg RA=235.63deg / 15.71hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127790_event45902607_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127853_Subrun00000000_00000185_event67093193.i3.zst -n Run00127853   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127853   -o /mnt/output_files/Run00127853_event67093193_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127853          at (nside,pix)=(16,1290) [llh=4036.65]: dec=9.59deg RA=239.06deg / 15.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127853_Subrun00000000_00000185_event67093193.i3.zst -n Run00127853   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1290,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127853   -o /mnt/output_files/Run00127853_event67093193_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127853          at (nside,pix)=(128,81494) [llh=3916.48]: dec=9.90deg RA=240.47deg / 16.03hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127853_Subrun00000000_00000185_event67093193.i3.zst -n Run00127853   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,81494,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127853   -o /mnt/output_files/Run00127853_event67093193_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127853          at (nside,pix)=(1024,5231278) [llh=3911.44]: dec=9.71deg RA=240.29deg / 16.02hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127853_event67093193_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127910_Subrun00000000_00000069_event25056152.i3.zst -n Run00127910   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00127910   -o /mnt/output_files/Run00127910_event25056152_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127910          at (nside,pix)=(16,1503) [llh=2445.90]: dec=2.39deg RA=354.38deg / 23.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127910_Subrun00000000_00000069_event25056152.i3.zst -n Run00127910   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1503,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00127910   -o /mnt/output_files/Run00127910_event25056152_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127910          at (nside,pix)=(128,95478) [llh=2412.57]: dec=1.79deg RA=353.32deg / 23.55hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2015_data_Run00127910_Subrun00000000_00000069_event25056152.i3.zst -n Run00127910   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,95478,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00127910   -o /mnt/output_files/Run00127910_event25056152_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00127910          at (nside,pix)=(1024,6084527) [llh=2410.56]: dec=1.90deg RA=352.88deg / 23.53hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00127910_event25056152_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128034_Subrun00000000_00000191_event69069846.i3.zst -n Run00128034   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128034   -o /mnt/output_files/Run00128034_event69069846_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128034          at (nside,pix)=(16,1314) [llh=884.89]: dec=7.18deg RA=11.25deg / 0.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128034_Subrun00000000_00000191_event69069846.i3.zst -n Run00128034   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1314,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128034   -o /mnt/output_files/Run00128034_event69069846_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128034          at (nside,pix)=(128,88344) [llh=771.67]: dec=5.68deg RA=16.88deg / 1.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128034_Subrun00000000_00000191_event69069846.i3.zst -n Run00128034   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,88344,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128034   -o /mnt/output_files/Run00128034_event69069846_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128034          at (nside,pix)=(1024,5777596) [llh=765.28]: dec=4.67deg RA=16.52deg / 1.10hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128034_event69069846_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128065_Subrun00000000_00000049_event17929326.i3.zst -n Run00128065   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128065   -o /mnt/output_files/Run00128065_event17929326_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128065          at (nside,pix)=(16,582) [llh=1112.75]: dec=38.68deg RA=213.75deg / 14.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128065_Subrun00000000_00000049_event17929326.i3.zst -n Run00128065   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,582,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128065   -o /mnt/output_files/Run00128065_event17929326_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128065          at (nside,pix)=(128,33841) [llh=1102.32]: dec=41.01deg RA=214.80deg / 14.32hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128065_Subrun00000000_00000049_event17929326.i3.zst -n Run00128065   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,33841,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128065   -o /mnt/output_files/Run00128065_event17929326_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128065          at (nside,pix)=(1024,2179467) [llh=1101.99]: dec=40.82deg RA=214.76deg / 14.32hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128065_event17929326_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128067_Subrun00000000_00000181_event65335330.i3.zst -n Run00128067   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128067   -o /mnt/output_files/Run00128067_event65335330_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128067          at (nside,pix)=(16,1238) [llh=2345.95]: dec=12.02deg RA=303.75deg / 20.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128067_Subrun00000000_00000181_event65335330.i3.zst -n Run00128067   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1238,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128067   -o /mnt/output_files/Run00128067_event65335330_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128067          at (nside,pix)=(128,76976) [llh=2332.34]: dec=12.64deg RA=304.10deg / 20.27hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128067_Subrun00000000_00000181_event65335330.i3.zst -n Run00128067   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,76976,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128067   -o /mnt/output_files/Run00128067_event65335330_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128067          at (nside,pix)=(1024,4916614) [llh=2331.00]: dec=12.64deg RA=304.32deg / 20.29hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128067_event65335330_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128209_Subrun00000000_00000150_event54386016.i3.zst -n Run00128209   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128209   -o /mnt/output_files/Run00128209_event54386016_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128209          at (nside,pix)=(16,1566) [llh=1319.10]: dec=0.00deg RA=351.56deg / 23.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128209_Subrun00000000_00000150_event54386016.i3.zst -n Run00128209   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1566,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128209   -o /mnt/output_files/Run00128209_event54386016_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128209          at (nside,pix)=(128,97523) [llh=1304.57]: dec=0.60deg RA=351.21deg / 23.41hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128209_Subrun00000000_00000150_event54386016.i3.zst -n Run00128209   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,97523,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128209   -o /mnt/output_files/Run00128209_event54386016_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128209          at (nside,pix)=(1024,6227870) [llh=1304.10]: dec=0.60deg RA=351.43deg / 23.43hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128209_event54386016_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128253_Subrun00000000_00000122_event44251618.i3.zst -n Run00128253   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128253   -o /mnt/output_files/Run00128253_event44251618_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128253          at (nside,pix)=(16,746) [llh=753.32]: dec=30.00deg RA=59.06deg / 3.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128253_Subrun00000000_00000122_event44251618.i3.zst -n Run00128253   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,746,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128253   -o /mnt/output_files/Run00128253_event44251618_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128253          at (nside,pix)=(128,50005) [llh=752.56]: dec=29.31deg RA=60.12deg / 4.01hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128253_Subrun00000000_00000122_event44251618.i3.zst -n Run00128253   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,50005,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128253   -o /mnt/output_files/Run00128253_event44251618_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128253          at (nside,pix)=(1024,3218093) [llh=752.48]: dec=29.23deg RA=60.25deg / 4.02hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128253_event44251618_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128278_Subrun00000000_00000136_event49218472.i3.zst -n Run00128278   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128278   -o /mnt/output_files/Run00128278_event49218472_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128278          at (nside,pix)=(16,1140) [llh=1427.82]: dec=14.48deg RA=115.31deg / 7.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128278_Subrun00000000_00000136_event49218472.i3.zst -n Run00128278   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1140,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128278   -o /mnt/output_files/Run00128278_event49218472_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128278          at (nside,pix)=(128,73121) [llh=1389.40]: dec=14.79deg RA=113.20deg / 7.55hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128278_Subrun00000000_00000136_event49218472.i3.zst -n Run00128278   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,73121,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128278   -o /mnt/output_files/Run00128278_event49218472_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128278          at (nside,pix)=(1024,4697351) [llh=1388.59]: dec=14.67deg RA=113.12deg / 7.54hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128278_event49218472_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128290_Subrun00000000_00000019_event6888376.i3.zst  -n Run00128290   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128290   -o /mnt/output_files/Run00128290_event6888376_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128290          at (nside,pix)=(16,1542) [llh=5193.33]: dec=0.00deg RA=216.56deg / 14.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128290_Subrun00000000_00000019_event6888376.i3.zst  -n Run00128290   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1542,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128290   -o /mnt/output_files/Run00128290_event6888376_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128290          at (nside,pix)=(128,98865) [llh=4811.40]: dec=-0.30deg RA=214.45deg / 14.30hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128290_Subrun00000000_00000019_event6888376.i3.zst  -n Run00128290   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,98865,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128290   -o /mnt/output_files/Run00128290_event6888376_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128290          at (nside,pix)=(1024,6324617) [llh=4809.68]: dec=-0.30deg RA=214.58deg / 14.31hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128290_event6888376_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128292_Subrun00000000_00000042_event15195696.i3.zst -n Run00128292   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128292   -o /mnt/output_files/Run00128292_event15195696_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128292          at (nside,pix)=(16,1047) [llh=1158.69]: dec=19.47deg RA=312.19deg / 20.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128292_Subrun00000000_00000042_event15195696.i3.zst -n Run00128292   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1047,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128292   -o /mnt/output_files/Run00128292_event15195696_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128292          at (nside,pix)=(128,64700) [llh=1156.11]: dec=20.11deg RA=312.54deg / 20.84hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128292_Subrun00000000_00000042_event15195696.i3.zst -n Run00128292   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,64700,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128292   -o /mnt/output_files/Run00128292_event15195696_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128292          at (nside,pix)=(1024,4134373) [llh=1155.90]: dec=20.07deg RA=312.63deg / 20.84hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128292_event15195696_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128311_Subrun00000000_00000073_event26552458.i3.zst -n Run00128311   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128311   -o /mnt/output_files/Run00128311_event26552458_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128311          at (nside,pix)=(16,1525) [llh=4109.73]: dec=0.00deg RA=120.94deg / 8.06hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128311_Subrun00000000_00000073_event26552458.i3.zst -n Run00128311   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1525,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128311   -o /mnt/output_files/Run00128311_event26552458_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128311          at (nside,pix)=(128,99246) [llh=4002.30]: dec=-0.60deg RA=122.70deg / 8.18hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128311_Subrun00000000_00000073_event26552458.i3.zst -n Run00128311   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,99246,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128311   -o /mnt/output_files/Run00128311_event26552458_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128311          at (nside,pix)=(1024,6368629) [llh=3996.99]: dec=-0.71deg RA=122.78deg / 8.19hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128311_event26552458_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128334_Subrun00000000_00000026_event9739548.i3.zst  -n Run00128334   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128334   -o /mnt/output_files/Run00128334_event9739548_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128334          at (nside,pix)=(16,377) [llh=410.13]: dec=48.14deg RA=86.79deg / 5.79hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128334_Subrun00000000_00000026_event9739548.i3.zst  -n Run00128334   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,377,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128334   -o /mnt/output_files/Run00128334_event9739548_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128334          at (nside,pix)=(128,24086) [llh=409.93]: dec=48.92deg RA=87.14deg / 5.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128334_Subrun00000000_00000026_event9739548.i3.zst  -n Run00128334   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,24086,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128334   -o /mnt/output_files/Run00128334_event9739548_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128334          at (nside,pix)=(1024,1554936) [llh=409.85]: dec=48.83deg RA=86.99deg / 5.80hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128334_event9739548_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128340_Subrun00000000_00000161_event58537957.i3.zst -n Run00128340   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128340   -o /mnt/output_files/Run00128340_event58537957_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128340          at (nside,pix)=(16,2371) [llh=3746.94]: dec=-32.80deg RA=196.88deg / 13.12hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128340_Subrun00000000_00000161_event58537957.i3.zst -n Run00128340   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,2371,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128340   -o /mnt/output_files/Run00128340_event58537957_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128340          at (nside,pix)=(128,150556) [llh=3697.02]: dec=-32.09deg RA=200.04deg / 13.34hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128340_Subrun00000000_00000161_event58537957.i3.zst -n Run00128340   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,150556,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128340   -o /mnt/output_files/Run00128340_event58537957_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128340          at (nside,pix)=(1024,9638116) [llh=3696.54]: dec=-32.13deg RA=200.04deg / 13.34hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128340_event58537957_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128547_Subrun00000000_00000040_event14557367.i3.zst -n Run00128547   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128547   -o /mnt/output_files/Run00128547_event14557367_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128547          at (nside,pix)=(16,1483) [llh=765.11]: dec=2.39deg RA=241.88deg / 16.12hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128547_Subrun00000000_00000040_event14557367.i3.zst -n Run00128547   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1483,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128547   -o /mnt/output_files/Run00128547_event14557367_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128547          at (nside,pix)=(128,95831) [llh=758.95]: dec=1.49deg RA=241.17deg / 16.08hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128547_Subrun00000000_00000040_event14557367.i3.zst -n Run00128547   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,95831,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128547   -o /mnt/output_files/Run00128547_event14557367_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128547          at (nside,pix)=(1024,6144695) [llh=758.79]: dec=1.34deg RA=241.13deg / 16.08hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128547_event14557367_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128567_Subrun00000000_00000058_event21044380.i3.zst -n Run00128567   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128567   -o /mnt/output_files/Run00128567_event21044380_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128567          at (nside,pix)=(16,642) [llh=1306.96]: dec=35.69deg RA=194.06deg / 12.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128567_Subrun00000000_00000058_event21044380.i3.zst -n Run00128567   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,642,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128567   -o /mnt/output_files/Run00128567_event21044380_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128567          at (nside,pix)=(128,38929) [llh=1286.39]: dec=37.17deg RA=192.30deg / 12.82hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128567_Subrun00000000_00000058_event21044380.i3.zst -n Run00128567   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,38929,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128567   -o /mnt/output_files/Run00128567_event21044380_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128567          at (nside,pix)=(1024,2494607) [llh=1285.69]: dec=37.12deg RA=192.57deg / 12.84hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128567_event21044380_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128606_Subrun00000000_00000150_event54200591.i3.zst -n Run00128606   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128606   -o /mnt/output_files/Run00128606_event54200591_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128606          at (nside,pix)=(16,1730) [llh=1712.22]: dec=-7.18deg RA=191.25deg / 12.75hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128606_Subrun00000000_00000150_event54200591.i3.zst -n Run00128606   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1730,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128606   -o /mnt/output_files/Run00128606_event54200591_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128606          at (nside,pix)=(128,111118) [llh=1702.18]: dec=-7.48deg RA=189.84deg / 12.66hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128606_Subrun00000000_00000150_event54200591.i3.zst -n Run00128606   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,111118,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128606   -o /mnt/output_files/Run00128606_event54200591_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128606          at (nside,pix)=(1024,7110770) [llh=1701.90]: dec=-7.48deg RA=190.06deg / 12.67hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128606_event54200591_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128632_Subrun00000000_00000173_event62194858.i3.zst -n Run00128632   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128632   -o /mnt/output_files/Run00128632_event62194858_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128632          at (nside,pix)=(16,885) [llh=1602.71]: dec=24.62deg RA=120.94deg / 8.06hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128632_Subrun00000000_00000173_event62194858.i3.zst -n Run00128632   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,885,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128632   -o /mnt/output_files/Run00128632_event62194858_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128632          at (nside,pix)=(128,58797) [llh=1595.67]: dec=23.64deg RA=121.64deg / 8.11hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128632_Subrun00000000_00000173_event62194858.i3.zst -n Run00128632   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,58797,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128632   -o /mnt/output_files/Run00128632_event62194858_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128632          at (nside,pix)=(1024,3759461) [llh=1595.30]: dec=23.72deg RA=121.42deg / 8.09hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128632_event62194858_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128651_Subrun00000000_00000123_event44166050.i3.zst -n Run00128651   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128651   -o /mnt/output_files/Run00128651_event44166050_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128651          at (nside,pix)=(16,1461) [llh=1571.29]: dec=2.39deg RA=118.13deg / 7.88hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128651_Subrun00000000_00000123_event44166050.i3.zst -n Run00128651   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1461,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128651   -o /mnt/output_files/Run00128651_event44166050_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128651          at (nside,pix)=(128,95145) [llh=1555.94]: dec=1.79deg RA=119.18deg / 7.95hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128651_Subrun00000000_00000123_event44166050.i3.zst -n Run00128651   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,95145,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128651   -o /mnt/output_files/Run00128651_event44166050_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128651          at (nside,pix)=(1024,6122826) [llh=1555.82]: dec=1.53deg RA=119.00deg / 7.93hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128651_event44166050_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128672_Subrun00000000_00000107_event38561326.i3.zst -n Run00128672   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128672   -o /mnt/output_files/Run00128672_event38561326_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128672          at (nside,pix)=(16,1191) [llh=3293.17]: dec=12.02deg RA=39.38deg / 2.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128672_Subrun00000000_00000107_event38561326.i3.zst -n Run00128672   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1191,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128672   -o /mnt/output_files/Run00128672_event38561326_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128672          at (nside,pix)=(128,76602) [llh=3174.11]: dec=12.64deg RA=41.13deg / 2.74hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128672_Subrun00000000_00000107_event38561326.i3.zst -n Run00128672   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,76602,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128672   -o /mnt/output_files/Run00128672_event38561326_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128672          at (nside,pix)=(1024,4925905) [llh=3171.33]: dec=12.52deg RA=40.87deg / 2.72hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128672_event38561326_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128755_Subrun00000000_00000090_event32356079.i3.zst -n Run00128755   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128755   -o /mnt/output_files/Run00128755_event32356079_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128755          at (nside,pix)=(16,1454) [llh=1435.58]: dec=2.39deg RA=78.75deg / 5.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128755_Subrun00000000_00000090_event32356079.i3.zst -n Run00128755   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1454,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128755   -o /mnt/output_files/Run00128755_event32356079_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128755          at (nside,pix)=(128,95600) [llh=1430.95]: dec=1.49deg RA=78.75deg / 5.25hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128755_Subrun00000000_00000090_event32356079.i3.zst -n Run00128755   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,95600,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128755   -o /mnt/output_files/Run00128755_event32356079_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128755          at (nside,pix)=(1024,6114175) [llh=1430.59]: dec=1.60deg RA=78.66deg / 5.24hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128755_event32356079_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128785_Subrun00000000_00000216_event76992952.i3.zst -n Run00128785   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128785   -o /mnt/output_files/Run00128785_event76992952_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128785          at (nside,pix)=(16,1529) [llh=2576.05]: dec=0.00deg RA=143.44deg / 9.56hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128785_Subrun00000000_00000216_event76992952.i3.zst -n Run00128785   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1529,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128785   -o /mnt/output_files/Run00128785_event76992952_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128785          at (nside,pix)=(128,98759) [llh=2471.37]: dec=-0.30deg RA=139.92deg / 9.33hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128785_Subrun00000000_00000216_event76992952.i3.zst -n Run00128785   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,98759,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128785   -o /mnt/output_files/Run00128785_event76992952_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128785          at (nside,pix)=(1024,6303289) [llh=2470.79]: dec=-0.11deg RA=140.01deg / 9.33hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128785_event76992952_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128796_Subrun00000000_00000074_event26367207.i3.zst -n Run00128796   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128796   -o /mnt/output_files/Run00128796_event26367207_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128796          at (nside,pix)=(16,76) [llh=993.20]: dec=72.39deg RA=247.50deg / 16.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128796_Subrun00000000_00000074_event26367207.i3.zst -n Run00128796   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,76,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128796   -o /mnt/output_files/Run00128796_event26367207_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128796          at (nside,pix)=(128,4271) [llh=992.25]: dec=73.13deg RA=257.28deg / 17.15hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128796_Subrun00000000_00000074_event26367207.i3.zst -n Run00128796   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,4271,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128796   -o /mnt/output_files/Run00128796_event26367207_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128796          at (nside,pix)=(1024,266764) [llh=992.16]: dec=73.27deg RA=257.55deg / 17.17hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128796_event26367207_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128906_Subrun00000000_00000225_event80127519.i3.zst -n Run00128906   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128906   -o /mnt/output_files/Run00128906_event80127519_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128906          at (nside,pix)=(16,1128) [llh=2512.71]: dec=14.48deg RA=47.81deg / 3.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128906_Subrun00000000_00000225_event80127519.i3.zst -n Run00128906   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1128,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128906   -o /mnt/output_files/Run00128906_event80127519_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128906          at (nside,pix)=(128,72002) [llh=2481.32]: dec=15.40deg RA=46.41deg / 3.09hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128906_Subrun00000000_00000225_event80127519.i3.zst -n Run00128906   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,72002,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128906   -o /mnt/output_files/Run00128906_event80127519_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128906          at (nside,pix)=(1024,4635151) [llh=2480.21]: dec=15.25deg RA=46.36deg / 3.09hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128906_event80127519_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128967_Subrun00000000_00000049_event17750653.i3.zst -n Run00128967   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00128967   -o /mnt/output_files/Run00128967_event17750653_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128967          at (nside,pix)=(16,1067) [llh=1569.88]: dec=16.96deg RA=61.87deg / 4.12hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128967_Subrun00000000_00000049_event17750653.i3.zst -n Run00128967   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1067,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00128967   -o /mnt/output_files/Run00128967_event17750653_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128967          at (nside,pix)=(128,68439) [llh=1561.79]: dec=17.58deg RA=61.52deg / 4.10hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00128967_Subrun00000000_00000049_event17750653.i3.zst -n Run00128967   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,68439,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00128967   -o /mnt/output_files/Run00128967_event17750653_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00128967          at (nside,pix)=(1024,4369087) [llh=1561.38]: dec=17.78deg RA=61.79deg / 4.12hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00128967_event17750653_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129020_Subrun00000000_00000057_event20626582.i3.zst -n Run00129020   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129020   -o /mnt/output_files/Run00129020_event20626582_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129020          at (nside,pix)=(16,1367) [llh=817.23]: dec=7.18deg RA=309.38deg / 20.63hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129020_Subrun00000000_00000057_event20626582.i3.zst -n Run00129020   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1367,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129020   -o /mnt/output_files/Run00129020_event20626582_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129020          at (nside,pix)=(128,84665) [llh=809.67]: dec=8.08deg RA=310.08deg / 20.67hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129020_Subrun00000000_00000057_event20626582.i3.zst -n Run00129020   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,84665,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129020   -o /mnt/output_files/Run00129020_event20626582_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129020          at (nside,pix)=(1024,5400006) [llh=809.65]: dec=8.16deg RA=309.95deg / 20.66hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129020_event20626582_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129144_Subrun00000000_00000185_event66284903.i3.zst -n Run00129144   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129144   -o /mnt/output_files/Run00129144_event66284903_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129144          at (nside,pix)=(16,704) [llh=2024.89]: dec=32.80deg RA=180.00deg / 12.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129144_Subrun00000000_00000185_event66284903.i3.zst -n Run00129144   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,704,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129144   -o /mnt/output_files/Run00129144_event66284903_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129144          at (nside,pix)=(128,44545) [llh=2020.25]: dec=33.15deg RA=180.70deg / 12.05hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129144_Subrun00000000_00000185_event66284903.i3.zst -n Run00129144   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,44545,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129144   -o /mnt/output_files/Run00129144_event66284903_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129144          at (nside,pix)=(128,44545) [llh=2020.25]: dec=33.15deg RA=180.70deg / 12.05hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129144_event66284903_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129153_Subrun00000000_00000032_event11436007.i3.zst -n Run00129153   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129153   -o /mnt/output_files/Run00129153_event11436007_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129153          at (nside,pix)=(16,1074) [llh=1429.83]: dec=16.96deg RA=101.25deg / 6.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129153_Subrun00000000_00000032_event11436007.i3.zst -n Run00129153   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1074,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129153   -o /mnt/output_files/Run00129153_event11436007_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129153          at (nside,pix)=(128,69517) [llh=1415.42]: dec=16.96deg RA=99.49deg / 6.63hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129153_Subrun00000000_00000032_event11436007.i3.zst -n Run00129153   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,69517,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129153   -o /mnt/output_files/Run00129153_event11436007_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129153          at (nside,pix)=(1024,4467822) [llh=1415.17]: dec=16.84deg RA=99.67deg / 6.64hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129153_event11436007_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129154_Subrun00000000_00000127_event45298080.i3.zst -n Run00129154   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129154   -o /mnt/output_files/Run00129154_event45298080_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129154          at (nside,pix)=(16,1392) [llh=1521.40]: dec=4.78deg RA=92.81deg / 6.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129154_Subrun00000000_00000127_event45298080.i3.zst -n Run00129154   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1392,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129154   -o /mnt/output_files/Run00129154_event45298080_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129154          at (nside,pix)=(128,90500) [llh=1519.94]: dec=4.48deg RA=92.81deg / 6.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129154_Subrun00000000_00000127_event45298080.i3.zst -n Run00129154   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,90500,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129154   -o /mnt/output_files/Run00129154_event45298080_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129154          at (nside,pix)=(1024,5786656) [llh=1519.62]: dec=4.59deg RA=92.81deg / 6.19hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129154_event45298080_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129232_Subrun00000000_00000143_event51118868.i3.zst -n Run00129232   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129232   -o /mnt/output_files/Run00129232_event51118868_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129232          at (nside,pix)=(16,1412) [llh=1251.47]: dec=4.78deg RA=205.31deg / 13.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129232_Subrun00000000_00000143_event51118868.i3.zst -n Run00129232   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1412,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129232   -o /mnt/output_files/Run00129232_event51118868_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129232          at (nside,pix)=(128,91171) [llh=1239.75]: dec=4.18deg RA=204.96deg / 13.66hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129232_Subrun00000000_00000143_event51118868.i3.zst -n Run00129232   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,91171,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129232   -o /mnt/output_files/Run00129232_event51118868_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129232          at (nside,pix)=(1024,5824797) [llh=1239.42]: dec=4.26deg RA=205.09deg / 13.67hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129232_event51118868_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129267_Subrun00000000_00000095_event34234803.i3.zst -n Run00129267   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129267   -o /mnt/output_files/Run00129267_event34234803_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129267          at (nside,pix)=(16,1403) [llh=1907.68]: dec=4.78deg RA=154.69deg / 10.31hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129267_Subrun00000000_00000095_event34234803.i3.zst -n Run00129267   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1403,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129267   -o /mnt/output_files/Run00129267_event34234803_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129267          at (nside,pix)=(128,88541) [llh=1879.59]: dec=5.68deg RA=155.39deg / 10.36hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129267_Subrun00000000_00000095_event34234803.i3.zst -n Run00129267   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,88541,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129267   -o /mnt/output_files/Run00129267_event34234803_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129267          at (nside,pix)=(1024,5684967) [llh=1878.80]: dec=5.53deg RA=155.35deg / 10.36hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129267_event34234803_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129307_Subrun00000000_00000224_event80305071.i3.zst -n Run00129307   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129307   -o /mnt/output_files/Run00129307_event80305071_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129307          at (nside,pix)=(16,1905) [llh=3473.80]: dec=-14.48deg RA=98.44deg / 6.56hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129307_Subrun00000000_00000224_event80305071.i3.zst -n Run00129307   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1905,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129307   -o /mnt/output_files/Run00129307_event80305071_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129307          at (nside,pix)=(128,123787) [llh=3465.85]: dec=-15.09deg RA=98.09deg / 6.54hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129307_Subrun00000000_00000224_event80305071.i3.zst -n Run00129307   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,123787,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129307   -o /mnt/output_files/Run00129307_event80305071_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129307          at (nside,pix)=(1024,7924830) [llh=3463.97]: dec=-15.06deg RA=98.26deg / 6.55hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129307_event80305071_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129420_Subrun00000000_00000166_event59928529.i3.zst -n Run00129420   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129420   -o /mnt/output_files/Run00129420_event59928529_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129420          at (nside,pix)=(16,1418) [llh=947.49]: dec=4.78deg RA=239.06deg / 15.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129420_Subrun00000000_00000166_event59928529.i3.zst -n Run00129420   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1418,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129420   -o /mnt/output_files/Run00129420_event59928529_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129420          at (nside,pix)=(128,89174) [llh=928.25]: dec=5.38deg RA=240.82deg / 16.05hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129420_Subrun00000000_00000166_event59928529.i3.zst -n Run00129420   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,89174,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129420   -o /mnt/output_files/Run00129420_event59928529_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129420          at (nside,pix)=(1024,5685941) [llh=927.08]: dec=5.53deg RA=240.95deg / 16.06hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129420_event59928529_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129434_Subrun00000000_00000163_event58903823.i3.zst -n Run00129434   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129434   -o /mnt/output_files/Run00129434_event58903823_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129434          at (nside,pix)=(16,2206) [llh=1332.76]: dec=-24.62deg RA=351.56deg / 23.44hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129434_Subrun00000000_00000163_event58903823.i3.zst -n Run00129434   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,2206,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129434   -o /mnt/output_files/Run00129434_event58903823_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129434          at (nside,pix)=(128,124655) [llh=1262.08]: dec=-15.40deg RA=348.05deg / 23.20hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129434_Subrun00000000_00000163_event58903823.i3.zst -n Run00129434   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,124655,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129434   -o /mnt/output_files/Run00129434_event58903823_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129434          at (nside,pix)=(1024,7858059) [llh=1234.48]: dec=-14.40deg RA=349.76deg / 23.32hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129434_event58903823_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129506_Subrun00000000_00000058_event21161807.i3.zst -n Run00129506_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129506_0 -o /mnt/output_files/Run00129506_event21161807_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129506_0        at (nside,pix)=(16,1047) [llh=1664.14]: dec=19.47deg RA=312.19deg / 20.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129506_Subrun00000000_00000058_event21161807.i3.zst -n Run00129506_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1047,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129506_0 -o /mnt/output_files/Run00129506_event21161807_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129506_0        at (nside,pix)=(128,67260) [llh=1656.58]: dec=18.52deg RA=312.19deg / 20.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129506_Subrun00000000_00000058_event21161807.i3.zst -n Run00129506_0 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,67260,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129506_0 -o /mnt/output_files/Run00129506_event21161807_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129506_0        at (nside,pix)=(1024,4285917) [llh=1654.19]: dec=18.60deg RA=311.97deg / 20.80hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129506_event21161807_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129506_Subrun00000000_00000137_event49650572.i3.zst -n Run00129506_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129506_1 -o /mnt/output_files/Run00129506_event49650572_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129506_1        at (nside,pix)=(16,776) [llh=1247.64]: dec=30.00deg RA=227.81deg / 15.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129506_Subrun00000000_00000137_event49650572.i3.zst -n Run00129506_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,776,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129506_1 -o /mnt/output_files/Run00129506_event49650572_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129506_1        at (nside,pix)=(128,48195) [llh=1231.11]: dec=30.69deg RA=227.46deg / 15.16hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2016_data_Run00129506_Subrun00000000_00000137_event49650572.i3.zst -n Run00129506_1 --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,48195,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129506_1 -o /mnt/output_files/Run00129506_event49650572_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129506_1        at (nside,pix)=(1024,3084827) [llh=1230.74]: dec=30.65deg RA=227.37deg / 15.16hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129506_event49650572_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2017_data_Run00129550_Subrun00000000_00000142_event51402681.i3.zst -n Run00129550   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129550   -o /mnt/output_files/Run00129550_event51402681_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129550          at (nside,pix)=(16,832) [llh=1000.11]: dec=27.28deg RA=180.00deg / 12.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2017_data_Run00129550_Subrun00000000_00000142_event51402681.i3.zst -n Run00129550   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,832,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129550   -o /mnt/output_files/Run00129550_event51402681_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129550          at (nside,pix)=(128,54782) [llh=992.44]: dec=26.28deg RA=178.59deg / 11.91hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2pass2_IC86.2017_data_Run00129550_Subrun00000000_00000142_event51402681.i3.zst -n Run00129550   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,54782,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129550   -o /mnt/output_files/Run00129550_event51402681_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129550          at (nside,pix)=(1024,3485680) [llh=992.24]: dec=26.49deg RA=178.59deg / 11.91hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129550_event51402681_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129654_Subrun00000000_00000022_event8332254.i3.zst       -n Run00129654   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129654   -o /mnt/output_files/Run00129654_event8332254_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129654          at (nside,pix)=(16,877) [llh=754.98]: dec=24.62deg RA=75.94deg / 5.06hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129654_Subrun00000000_00000022_event8332254.i3.zst       -n Run00129654   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,877,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129654   -o /mnt/output_files/Run00129654_event8332254_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129654          at (nside,pix)=(128,56170) [llh=753.89]: dec=25.28deg RA=74.88deg / 4.99hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129654_Subrun00000000_00000022_event8332254.i3.zst       -n Run00129654   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,56170,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129654   -o /mnt/output_files/Run00129654_event8332254_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129654          at (nside,pix)=(1024,3623765) [llh=753.87]: dec=25.08deg RA=74.97deg / 5.00hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129654_event8332254_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129677_Subrun00000000_00000157_event55886338.i3.zst      -n Run00129677   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129677   -o /mnt/output_files/Run00129677_event55886338_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129677          at (nside,pix)=(16,1298) [llh=944.75]: dec=9.59deg RA=284.06deg / 18.94hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129677_Subrun00000000_00000157_event55886338.i3.zst      -n Run00129677   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1298,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129677   -o /mnt/output_files/Run00129677_event55886338_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129677          at (nside,pix)=(128,83600) [llh=893.43]: dec=8.69deg RA=281.25deg / 18.75hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129677_Subrun00000000_00000157_event55886338.i3.zst      -n Run00129677   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,83600,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129677   -o /mnt/output_files/Run00129677_event55886338_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129677          at (nside,pix)=(1024,5330045) [llh=892.47]: dec=8.80deg RA=280.99deg / 18.73hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129677_event55886338_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129701_Subrun00000000_00000144_event49353375.i3.zst      -n Run00129701   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129701   -o /mnt/output_files/Run00129701_event49353375_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129701          at (nside,pix)=(16,969) [llh=1556.01]: dec=22.02deg RA=230.62deg / 15.37hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129701_Subrun00000000_00000144_event49353375.i3.zst      -n Run00129701   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,969,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129701   -o /mnt/output_files/Run00129701_event49353375_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129701          at (nside,pix)=(128,59463) [llh=1492.43]: dec=23.32deg RA=230.27deg / 15.35hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129701_Subrun00000000_00000144_event49353375.i3.zst      -n Run00129701   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,59463,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129701   -o /mnt/output_files/Run00129701_event49353375_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129701          at (nside,pix)=(1024,3797566) [llh=1491.48]: dec=23.36deg RA=230.45deg / 15.36hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129701_event49353375_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129777_Subrun00000000_00000187_event67372962.i3.zst      -n Run00129777   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129777   -o /mnt/output_files/Run00129777_event67372962_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129777          at (nside,pix)=(16,837) [llh=2414.79]: dec=27.28deg RA=208.12deg / 13.88hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129777_Subrun00000000_00000187_event67372962.i3.zst      -n Run00129777   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,837,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129777   -o /mnt/output_files/Run00129777_event67372962_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129777          at (nside,pix)=(128,56360) [llh=2350.06]: dec=25.28deg RA=208.48deg / 13.90hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129777_Subrun00000000_00000187_event67372962.i3.zst      -n Run00129777   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,56360,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129777   -o /mnt/output_files/Run00129777_event67372962_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129777          at (nside,pix)=(1024,3617091) [llh=2348.55]: dec=25.16deg RA=208.39deg / 13.89hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129777_event67372962_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129855_Subrun00000000_00000106_event33565191.i3.zst      -n Run00129855   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129855   -o /mnt/output_files/Run00129855_event33565191_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129855          at (nside,pix)=(16,1376) [llh=649.37]: dec=4.78deg RA=2.81deg / 0.19hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129855_Subrun00000000_00000106_event33565191.i3.zst      -n Run00129855   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1376,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129855   -o /mnt/output_files/Run00129855_event33565191_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129855          at (nside,pix)=(128,90370) [llh=637.82]: dec=4.48deg RA=1.41deg / 0.09hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129855_Subrun00000000_00000106_event33565191.i3.zst      -n Run00129855   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,90370,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129855   -o /mnt/output_files/Run00129855_event33565191_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129855          at (nside,pix)=(1024,5781516) [llh=632.11]: dec=4.63deg RA=1.10deg / 0.07hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129855_event33565191_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129878_Subrun00000000_00000118_event40814378.i3.zst      -n Run00129878   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129878   -o /mnt/output_files/Run00129878_event40814378_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129878          at (nside,pix)=(16,1572) [llh=2388.78]: dec=-2.39deg RA=22.50deg / 1.50hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129878_Subrun00000000_00000118_event40814378.i3.zst      -n Run00129878   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1572,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129878   -o /mnt/output_files/Run00129878_event40814378_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129878          at (nside,pix)=(128,102174) [llh=2323.76]: dec=-2.39deg RA=21.45deg / 1.43hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129878_Subrun00000000_00000118_event40814378.i3.zst      -n Run00129878   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,102174,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129878   -o /mnt/output_files/Run00129878_event40814378_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129878          at (nside,pix)=(1024,6539506) [llh=2321.90]: dec=-2.28deg RA=21.27deg / 1.42hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129878_event40814378_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129915_Subrun00000000_00000198_event72252401.i3.zst      -n Run00129915   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129915   -o /mnt/output_files/Run00129915_event72252401_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129915          at (nside,pix)=(16,996) [llh=918.10]: dec=19.47deg RA=25.31deg / 1.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129915_Subrun00000000_00000198_event72252401.i3.zst      -n Run00129915   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,996,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129915   -o /mnt/output_files/Run00129915_event72252401_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129915          at (nside,pix)=(128,66342) [llh=897.87]: dec=18.84deg RA=27.07deg / 1.80hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129915_Subrun00000000_00000198_event72252401.i3.zst      -n Run00129915   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,66342,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129915   -o /mnt/output_files/Run00129915_event72252401_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129915          at (nside,pix)=(1024,4254003) [llh=897.47]: dec=18.88deg RA=26.98deg / 1.80hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129915_event72252401_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129933_Subrun00000000_00000091_event32926212.i3.zst      -n Run00129933   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00129933   -o /mnt/output_files/Run00129933_event32926212_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129933          at (nside,pix)=(16,1191) [llh=686.26]: dec=12.02deg RA=39.38deg / 2.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129933_Subrun00000000_00000091_event32926212.i3.zst      -n Run00129933   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1191,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00129933   -o /mnt/output_files/Run00129933_event32926212_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129933          at (nside,pix)=(128,77116) [llh=656.52]: dec=12.33deg RA=42.19deg / 2.81hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00129933_Subrun00000000_00000091_event32926212.i3.zst      -n Run00129933   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,77116,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00129933   -o /mnt/output_files/Run00129933_event32926212_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00129933          at (nside,pix)=(1024,4942301) [llh=656.03]: dec=12.37deg RA=41.92deg / 2.79hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00129933_event32926212_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130033_Subrun00000000_00000145_event50579430.i3.zst      -n Run00130033   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00130033   -o /mnt/output_files/Run00130033_event50579430_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130033          at (nside,pix)=(16,1326) [llh=2465.09]: dec=7.18deg RA=78.75deg / 5.25hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130033_Subrun00000000_00000145_event50579430.i3.zst      -n Run00130033   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1326,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00130033   -o /mnt/output_files/Run00130033_event50579430_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130033          at (nside,pix)=(128,88430) [llh=2331.51]: dec=5.68deg RA=77.34deg / 5.16hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130033_Subrun00000000_00000145_event50579430.i3.zst      -n Run00130033   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,88430,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00130033   -o /mnt/output_files/Run00130033_event50579430_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130033          at (nside,pix)=(1024,5655409) [llh=2327.38]: dec=5.79deg RA=77.43deg / 5.16hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00130033_event50579430_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130034_Subrun00000000_00000022_event7858514.i3.zst       -n Run00130034   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00130034   -o /mnt/output_files/Run00130034_event7858514_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130034          at (nside,pix)=(16,1599) [llh=1461.34]: dec=-2.39deg RA=174.38deg / 11.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130034_Subrun00000000_00000022_event7858514.i3.zst       -n Run00130034   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1599,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00130034   -o /mnt/output_files/Run00130034_event7858514_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130034          at (nside,pix)=(128,102903) [llh=1454.08]: dec=-2.69deg RA=173.67deg / 11.58hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130034_Subrun00000000_00000022_event7858514.i3.zst       -n Run00130034   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,102903,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00130034   -o /mnt/output_files/Run00130034_event7858514_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130034          at (nside,pix)=(1024,6569909) [llh=1453.30]: dec=-2.54deg RA=173.45deg / 11.56hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00130034_event7858514_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130092_Subrun00000000_00000086_event30964247.i3.zst      -n Run00130092   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00130092   -o /mnt/output_files/Run00130092_event30964247_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130092          at (nside,pix)=(16,1079) [llh=1374.38]: dec=16.96deg RA=129.38deg / 8.62hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130092_Subrun00000000_00000086_event30964247.i3.zst      -n Run00130092   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1079,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00130092   -o /mnt/output_files/Run00130092_event30964247_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130092          at (nside,pix)=(128,69053) [llh=1309.30]: dec=17.27deg RA=132.89deg / 8.86hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130092_Subrun00000000_00000086_event30964247.i3.zst      -n Run00130092   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,69053,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00130092   -o /mnt/output_files/Run00130092_event30964247_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130092          at (nside,pix)=(1024,4427237) [llh=1308.85]: dec=17.23deg RA=132.63deg / 8.84hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00130092_event30964247_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130126_Subrun00000000_00000160_event56068624.i3.zst      -n Run00130126   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00130126   -o /mnt/output_files/Run00130126_event56068624_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130126          at (nside,pix)=(16,1981) [llh=1600.39]: dec=-16.96deg RA=163.12deg / 10.88hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130126_Subrun00000000_00000160_event56068624.i3.zst      -n Run00130126   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1981,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00130126   -o /mnt/output_files/Run00130126_event56068624_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130126          at (nside,pix)=(128,124392) [llh=1583.20]: dec=-15.40deg RA=163.12deg / 10.88hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130126_Subrun00000000_00000160_event56068624.i3.zst      -n Run00130126   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,124392,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00130126   -o /mnt/output_files/Run00130126_event56068624_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130126          at (nside,pix)=(1024,7970621) [llh=1582.65]: dec=-15.48deg RA=162.91deg / 10.86hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00130126_event56068624_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130172_Subrun00000000_00000161_event52824390.i3.zst      -n Run00130172   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00130172   -o /mnt/output_files/Run00130172_event52824390_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130172          at (nside,pix)=(16,1556) [llh=842.92]: dec=0.00deg RA=295.31deg / 19.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130172_Subrun00000000_00000161_event52824390.i3.zst      -n Run00130172   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1556,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00130172   -o /mnt/output_files/Run00130172_event52824390_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130172          at (nside,pix)=(128,94883) [llh=834.55]: dec=2.09deg RA=294.61deg / 19.64hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130172_Subrun00000000_00000161_event52824390.i3.zst      -n Run00130172   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,94883,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00130172   -o /mnt/output_files/Run00130172_event52824390_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130172          at (nside,pix)=(1024,6067479) [llh=834.50]: dec=2.05deg RA=294.52deg / 19.63hours
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00130172_event52824390_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130214_Subrun00000000_00000054_event17569642.i3.zst      -n Run00130214   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00130214   -o /mnt/output_files/Run00130214_event17569642_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130214          at (nside,pix)=(16,1372) [llh=4446.76]: dec=7.18deg RA=337.50deg / 22.50hours 
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130214_Subrun00000000_00000054_event17569642.i3.zst      -n Run00130214   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,1372,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00130214   -o /mnt/output_files/Run00130214_event17569642_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130214          at (nside,pix)=(128,85732) [llh=3781.65]: dec=7.48deg RA=340.31deg / 22.69hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130214_Subrun00000000_00000054_event17569642.i3.zst      -n Run00130214   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,85732,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00130214   -o /mnt/output_files/Run00130214_event17569642_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130214          at (nside,pix)=(1024,5478174) [llh=3779.42]: dec=7.44deg RA=340.14deg / 22.68hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00130214_event17569642_scanned1024.i3.zst
CHECK!

####################################################################

# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130220_Subrun00000000_00000036_event11599241.i3.zst      -n Run00130220   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 16 -n Run00130220   -o /mnt/output_files/Run00130220_event11599241_scanned16.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130220          at (nside,pix)=(16,2128) [llh=18015.81]: dec=-22.02deg RA=270.00deg / 18.00hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130220_Subrun00000000_00000036_event11599241.i3.zst      -n Run00130220   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 --area 16,2128,3000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 128 -n Run00130220   -o /mnt/output_files/Run00130220_event11599241_scanned128.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130220          at (nside,pix)=(128,133247) [llh=16193.79]: dec=-20.74deg RA=269.65deg / 17.98hours
# docker run --rm -ti -v $PWD:/mnt icecube/skymap_scanner:latest producer /mnt/input_files/Level2_IC86.2017_data_Run00130220_Subrun00000000_00000036_event11599241.i3.zst      -n Run00130220   --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 --area 128,133247,6000 --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
# docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar+ssl://pulsar.api.icecube.aq:6651 --nside 1024 -n Run00130220   -o /mnt/output_files/Run00130220_event11599241_scanned1024.i3.zst --auth-token `cat aws_ec2/pulsar_terraform_ansible/secrets/icecube.skymap.token`
  ** best entry for Run00130220          at (nside,pix)=(1024,8516604) [llh=16192.62]: dec=-20.70deg RA=269.65deg / 17.98hours 
# docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/output_files/Run00130220_event11599241_scanned1024.i3.zst
CHECK!

####################################################################



