"""The Worker service."""


# fmt: off
# mypy: ignore-errors
# pylint: skip-file

import os
import platform

from I3Tray import I3Units
from icecube import dataclasses, distribute, icetray


@icetray.traysegment
def scan_pixel_distributed(tray, name,
    port=5555,
    ExcludedDOMs=[],
    NumClients=10,
    pulsesName="SplitUncleanedInIcePulsesLatePulseCleaned",
    base_GCD_paths=[os.path.join(os.environ["I3_DATA"],'GCD')],
    base_GCD_filename='GeoCalibDetectorStatus_2015.57161_V0.i3.gz',
    RemoteSubmitPrefix=''): # 'ssh submitter'

    def makeSurePulsesExist(frame, pulsesName):
        if pulsesName not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName))
        if pulsesName+"TimeWindows" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeWindows"))
        if pulsesName+"TimeRange" not in frame:
            raise RuntimeError("{0} not in frame".format(pulsesName+"TimeRange"))
    tray.AddModule(makeSurePulsesExist, name+"_makeSurePulsesExist", pulsesName=pulsesName)

    tray.Add(distribute.I3DistributeToCondorClients, name+"_I3DistributeToCondorClients",
        Script = """
            #!/bin/sh {0}/icetray-start
            #METAPROJECT {1}

            import os
            import datetime
            import sys

            from I3Tray import *
            from icecube import icetray, dataio, dataclasses, recclasses, simclasses
            from icecube import photonics_service, gulliver, gulliver_modules, millipede
            from icecube import frame_object_diff
            from icecube import distribute

            pulsesName = "{5}"

            ########## load data

            # At HESE energies, deposited light is dominated by the stochastic losses
            # (muon part emits so little light in comparison)
            # This is why we can use ems_mie instead of InfBareMu_mie even for tracks
            base = os.path.expandvars('$I3_DATA/photon-tables/splines/ems_mie_z20_a10.%s.fits')
            cascade_service = photonics_service.I3PhotoSplineService(base % "abs", base % "prob", 0)

            basemu = os.path.expandvars('$I3_DATA/photon-tables/splines/InfBareMu_mie_%s_z20a10_V2.fits')
            # muon_service = photonics_service.I3PhotoSplineService(basemu % "abs", basemu% "prob", 0)
            muon_service = None

            iceModelBaseNames = {{"SpiceMie": "ems_mie_z20_a10", "Spice1": "ems_spice1_z20_a10"}}
            iceModelBaseName = iceModelBaseNames["SpiceMie"]

            SPEScale = 0.99

            ExcludedDOMs = {4}

            # find an available GCD base path
            stagers = dataio.get_stagers()
            base_GCD_paths = {6}
            base_GCD_filename = "{7}"

            # try to load the base file from the various possible input directories
            GCD_diff_base_handle = None
            if base_GCD_filename is not None and base_GCD_filename != "None":
                for GCD_base_dir in base_GCD_paths:
                    try:
                        read_url = os.path.join(GCD_base_dir, base_GCD_filename)
                        print("reading baseline GCD from {{0}}".format( read_url ))
                        GCD_diff_base_handle = stagers.GetReadablePath( read_url )
                        if not os.path.isfile( str(GCD_diff_base_handle) ):
                            raise RuntimeError("file does not exist (or is not a file)")
                    except:
                        print(" -> failed")
                        GCD_diff_base_handle=None
                    if GCD_diff_base_handle is not None:
                        print(" -> success")
                        break

                if GCD_diff_base_handle is None:
                    raise RuntimeError("Could not read the input GCD file '{{0}}' from any pre-configured location".format(base_GCD_filename))


            # connect to a server
            c = distribute.I3DistributeClient(
                WorkerScriptHash=distribute.sha1_of_main_script(),      # this is to ensure only the correct script is sending replies to the server
                ServerURL="tcp://{2}:{3}",
                DoNotPreRequestWork=True, # only request work once the current item has been returned
                )

            ########## the tray
            tray = I3Tray()
            # tray.context["I3FileStager"] = stagers

            tray.Add("I3DistributeSource", Client=c)

            ########## perform the fit

            def notifyStart(frame):
                print("got data - uncompressing GCD", datetime.datetime.now())
            tray.AddModule(notifyStart, "notifyStart")

            @icetray.traysegment
            def UncompressGCD(tray,name, base_GCD_path, base_GCD_filename):
                from icecube.frame_object_diff.segments import uncompress

                tray.Add(uncompress, name+"_GCD_patch",
                         keep_compressed=False,
                         base_path=base_GCD_path,
                         base_filename=base_GCD_filename)

            if GCD_diff_base_handle is not None:
                tray.Add(UncompressGCD, "GCD_uncompress",
                         base_GCD_path="",
                         base_GCD_filename=str(GCD_diff_base_handle))

            def notify0(frame):
                print("starting a new fit!", datetime.datetime.now())
            tray.AddModule(notify0, "notify0")

            tray.AddService('MillipedeLikelihoodFactory', 'millipedellh',
                MuonPhotonicsService=muon_service,
                CascadePhotonicsService=cascade_service,
                ShowerRegularization=0,
                PhotonsPerBin=15,
                DOMEfficiency=SPEScale,
                ExcludedDOMs=ExcludedDOMs,
                PartialExclusion=True,
                ReadoutWindow=pulsesName+'TimeRange',
                Pulses=pulsesName,
                BinSigma=3)

            tray.AddService('I3GSLRandomServiceFactory','I3RandomService')
            tray.AddService('I3GSLSimplexFactory', 'simplex',
                MaxIterations=20000)

            tray.AddService('MuMillipedeParametrizationFactory', 'coarseSteps',
                MuonSpacing=0.*I3Units.m,
                ShowerSpacing=5.*I3Units.m,
                StepX = 10.*I3Units.m,
                StepY = 10.*I3Units.m,
                StepZ = 10.*I3Units.m,
                StepT = 0.,
                StepZenith = 0.,
                StepAzimuth = 0.,
                )
            tray.AddService('I3BasicSeedServiceFactory', 'vetoseed',
                FirstGuesses=['MillipedeSeedParticle'],
                TimeShiftType='TNone',
                PositionShiftType='None')
            tray.AddModule('I3SimpleFitter', 'MillipedeStarting1stPass',
                OutputName='MillipedeStarting1stPass',
                SeedService='vetoseed',
                Parametrization='coarseSteps',
                LogLikelihood='millipedellh',
                Minimizer='simplex')


            def notify1(frame):
                print("1st pass done!", datetime.datetime.now())
                print("MillipedeStarting1stPass", frame["MillipedeStarting1stPass"])
            tray.AddModule(notify1, "notify1")

            tray.AddService('MuMillipedeParametrizationFactory', 'fineSteps',
                MuonSpacing=0.*I3Units.m,
                ShowerSpacing=2.5*I3Units.m,

                StepX = 2.*I3Units.m,
                StepY = 2.*I3Units.m,
                StepZ = 2.*I3Units.m,
                StepT = 5.*I3Units.ns, # now, also fit for time
                StepZenith = 0.,
                StepAzimuth = 0.,
                )
            tray.AddService('I3BasicSeedServiceFactory', 'firstFitSeed',
                FirstGuess='MillipedeStarting1stPass',
                TimeShiftType='TNone',
                PositionShiftType='None')
            tray.AddModule('I3SimpleFitter', 'MillipedeStarting2ndPass',
                OutputName='MillipedeStarting2ndPass',
                SeedService='firstFitSeed',
                Parametrization='fineSteps',
                LogLikelihood='millipedellh',
                Minimizer='simplex')


            def notify2(frame):
                print("2nd pass done!", datetime.datetime.now())
                print("MillipedeStarting2ndPass", frame["MillipedeStarting2ndPass"])
            tray.AddModule(notify2, "notify2")

            tray.Add("I3DistributeSink", Client=c)

            tray.AddModule('TrashCan', 'thecan')

            tray.Execute()
            tray.Finish()
            del tray
        """.format(
            os.environ["SROOTBASE"],
            os.environ["I3_BUILD"],
            platform.node(),
            port,
            ExcludedDOMs.__str__(),
            pulsesName,
            str(base_GCD_paths),
            base_GCD_filename
            ),
        NumClients=NumClients,
        RemoteSubmitPrefix=RemoteSubmitPrefix, # use this on cobalts to submit from "submitter" (needs ssh keys)
        ServerBindURL = "tcp://*:{0}".format(port), # listen on this port for connections from clients
        ZombieWorkerTimeout=240.*I3Units.second, # wait for 1 minute after we stopped hearing from a client before considering it dead
        QueueSize=1000000,
        WorkOnStreams=[icetray.I3Frame.Physics],
        ReportUsagePeriod=60.*I3Units.second)


def main() -> None:
    """Start up Worker service."""
    ExcludedDOMs = [
        'CalibrationErrata',
        'BadDomsList',
        'DeepCoreDOMs',
        'SaturatedDOMs',
        'BrightDOMs',
        'SplitUncleanedInIcePulsesLatePulseCleanedTimeWindows',
        ]

    tray.AddSegment(scan_pixel_distributed, "scan_pixel_distributed",
        port=port,
        ExcludedDOMs=ExcludedDOMs,
        NumClients=numclients,
        base_GCD_paths=config.GCD_base_dirs,
        base_GCD_filename=base_GCD_filename,
        RemoteSubmitPrefix=RemoteSubmitPrefix,
    )


if __name__ == "__main__":
    main()
