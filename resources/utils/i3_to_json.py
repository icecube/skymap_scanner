"""Helper script to extract CausalQTot and MJD data from i3 to h5."""

# mypy: ignore-errors
# fmt:off

import argparse
import json
import os

from I3Tray import I3Tray
from icecube import (
    MuonGun,
    VHESelfVeto,
    astro,
    dataclasses,
    gulliver,
    icetray,
    recclasses,
)
from icecube.filterscripts import alerteventfollowup, filter_globals
from icecube.full_event_followup import (
    frame_packet_to_i3live_json,
    i3live_json_to_frame_packet,
)


def alertify(frame):
    if 'SplitUncleanedInIcePulses' not in frame:
        return False

    if isinstance(frame['I3SuperDST'], dataclasses.I3RecoPulseSeriesMapApplySPECorrection):
        print('It seems like I3SuperDST is an instance of I3RecoPulseSeriesMapApplySPECorrection... converting to I3SuperDST')
        frame['I3SuperDST_tmp'] = frame['I3SuperDST']
        del frame['I3SuperDST']
        frame['I3SuperDST'] = dataclasses.I3SuperDST(
            dataclasses.I3RecoPulseSeriesMap.from_frame(frame, 'I3SuperDST_tmp'))
        
    print('It seems like your i3 file is missing some cool keys')
    print(frame)
    print('I will add some fake ones')
    if filter_globals.EHEAlertFilter not in frame:
        frame[filter_globals.EHEAlertFilter] = icetray.I3Bool(True)
    if 'OnlineL2_SplineMPE' not in frame:
        frame['OnlineL2_SplineMPE'] = dataclasses.I3Particle()
        frame['OnlineL2_SplineMPE_CramerRao_cr_zenith'] = dataclasses.I3Double(0)
        frame['OnlineL2_SplineMPE_CramerRao_cr_azimuth'] = dataclasses.I3Double(0)
        frame['OnlineL2_SplineMPE_MuE'] = dataclasses.I3Particle()
        frame['OnlineL2_SplineMPE_MuE'].energy=0
        frame['OnlineL2_SplineMPE_MuEx'] = dataclasses.I3Particle()
        frame['OnlineL2_SplineMPE_MuEx'].energy=0
    if 'IceTop_SLC_InTime' not in frame:
        frame['IceTop_SLC_InTime'] = icetray.I3Bool(False)

    if 'IceTop_HLC_InTime' not in frame:
        frame['IceTop_HLC_InTime'] = icetray.I3Bool(False)

    if 'OnlineL2_SPE2itFit' not in frame:
        frame['OnlineL2_SPE2itFit'] = dataclasses.I3Particle()
        frame['OnlineL2_SPE2itFitFitParams'] = gulliver.I3LogLikelihoodFitParams()

    if 'OnlineL2_BestFit' not in frame:
        frame['OnlineL2_BestFit'] = dataclasses.I3Particle()
        frame['OnlineL2_BestFit_Name'] = dataclasses.I3String("hi")
        frame['OnlineL2_BestFitFitParams'] = gulliver.I3LogLikelihoodFitParams()
        frame['OnlineL2_BestFit_CramerRao_cr_zenith'] = dataclasses.I3Double(0)
        frame['OnlineL2_BestFit_CramerRao_cr_azimuth'] = dataclasses.I3Double(0)
        frame['OnlineL2_BestFit_MuEx'] = dataclasses.I3Particle()
        frame['OnlineL2_BestFit_MuEx'].energy=0

    if 'PoleEHEOpheliaParticle_ImpLF' not in frame:
        frame['PoleEHEOpheliaParticle_ImpLF'] = dataclasses.I3Particle()
    if 'PoleEHESummaryPulseInfo' not in frame:
        frame['PoleEHESummaryPulseInfo'] = recclasses.I3PortiaEvent()


def write_json(frame, extra):
    pnf = frame_packet_to_i3live_json(i3live_json_to_frame_packet(
        frame[filter_globals.alert_candidate_full_message].value,
        pnf_framing=False), pnf_framing=True)
    msg = json.loads(frame[filter_globals.alert_candidate_full_message].value)
    pnfmsg = json.loads(pnf)
    fullmsg = {key: value for (key, value) in (list(msg.items()) + list(pnfmsg.items())) if key !='frames'}
    extra_namer = {'OnlineL2_SplineMPE':'ol2_mpe'}
    try:
        uid_sub = (fullmsg['run_id'],
                   fullmsg['event_id'],
                   frame['I3EventHeader'].sub_event_id)
        for i3part_key in extra[uid_sub]:
            part = extra[uid_sub][i3part_key]
            ra, dec = astro.dir_to_equa(
                part.dir.zenith, part.dir.azimuth,
                frame['I3EventHeader'].start_time.mod_julian_day_double)
            fullmsg[extra_namer.get(i3part_key, i3part_key)] = {'ra':ra.item(), 'dec':dec.item()}
    except KeyError as e:
        print('Q-frame was split into multiple P-frames, skipping subevents not in input i3 file', e)
        return False

    if 'I3MCTree' in frame:
        prim = dataclasses.get_most_energetic_primary(frame['I3MCTree'])
        muhi = dataclasses.get_most_energetic_muon(frame['I3MCTree'])
        ra, dec = astro.dir_to_equa(prim.dir.zenith, prim.dir.azimuth,
                                    frame['I3EventHeader'].start_time.mod_julian_day_double)

        edep = 0
        for track in MuonGun.Track.harvest(frame['I3MCTree'], frame['MMCTrackList']):
            # Find distance to entrance and exit from sampling volume
            intersections = VHESelfVeto.IntersectionsWithInstrumentedVolume(frame['I3Geometry'], track)
            # Get the corresponding energies
            e0, e1 = track.get_energy((intersections[0]-track.pos).magnitude), track.get_energy((intersections[1]-track.pos).magnitude)
            # Accumulate
            edep +=  (e0-e1)
        fullmsg['true'] = {'ra':ra.item(), 'dec':dec.item(), 'eprim': prim.energy, 'emuhi': muhi.energy, 'emuin':edep}

    jf = f'{fullmsg["unique_id"]}.sub{uid_sub[2]:03}.json'
    with open(jf, 'w') as f:
        json.dump(fullmsg, f)
        print(f'Wrote {jf}')


def extract_original(i3files, orig_keys):
    extracted = {}
    def pullout(frame):
        uid = (frame['I3EventHeader'].run_id,
               frame['I3EventHeader'].event_id,
               frame['I3EventHeader'].sub_event_id)
        dd = {}
        for ok in orig_keys:
            try:
                dd[ok] = frame[ok]
            except KeyError as e:
                print('KeyError:', e, uid)
        extracted[uid] = dd
    tray = I3Tray()
    tray.Add('I3Reader', Filenamelist=i3files)
    tray.Add(pullout)
    tray.Execute()
    return extracted


def main():
    parser = argparse.ArgumentParser(
        description='Extract CausalQTot and MJD data from i3 to h5')

    parser.add_argument('i3s', nargs='+', help='input i3s')
    parser.add_argument('--basegcd', default='/data/user/followup/baseline_gcds/baseline_gcd_136897.i3',
                        type=str,
                        help='baseline gcd file for creating the GCD diff')
    parser.add_argument('--nframes', type=int, default=None, help='number of frames to process')
    parser.add_argument('--extra', action='append',
                        default=[], help='extra I3Particles to pull out from original i3 file')
    parser.add_argument('-o', '--out', default='/dev/null',
                        help='output I3 file')
    args = parser.parse_args()

    extracted = extract_original(args.i3s, args.extra)

    tray = I3Tray()
    tray.Add('I3Reader', Filenamelist=args.i3s)
    icetray.load('libtrigger-splitter', False)
    tray.Add('Delete', Keys=['SplitUncleanedInIcePulses','SplitUncleanedInIcePulsesTimeRange'])
    tray.AddModule('I3TriggerSplitter','InIceSplit')(
        ("TrigHierName", 'DSTTriggers'), 
        ('InputResponses', ['InIceDSTPulses']),
        ('OutputResponses', ['SplitUncleanedInIcePulses']),
    )
    tray.Add(alertify)
    tray.Add(alerteventfollowup.AlertEventFollowup,
             base_GCD_path=os.path.dirname(args.basegcd),
             base_GCD_filename=os.path.basename(args.basegcd),
             If=lambda f: filter_globals.EHEAlertFilter in f)
    tray.Add(write_json, extra=extracted, If=lambda f: filter_globals.EHEAlertFilter in f)
    tray.AddModule('I3Writer',
                   'writer',
                   filename=args.out,
                   streams=[icetray.I3Frame.Physics,
                            icetray.I3Frame.DAQ])
    if args.nframes is None:
        tray.Execute()
    else:
        tray.Execute(args.nframes)
    tray.Finish()

    
if __name__ == '__main__':
    main()
