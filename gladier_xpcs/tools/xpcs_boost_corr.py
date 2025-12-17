from gladier import GladierBaseTool, generate_flow_definition

def xpcs_boost_corr(boost_corr: dict = None, corr_input_file: str = None, **data):
    """
    Run the boost corr tool on the given set of inputs within ``boost_corr``. Runs boost corr with
    the given inputs, and writes the results to the given 'output' directory listed in boost_corr.output.
    Additionally, writes a boost_corr.log file containing the stderr output of boost_corr. 


    There are multiple types of inputs that Boost Corr supports, and this tooling supports all of them.
    Typically this is opaque to the flow input, but it will change the type of file in boost_corr["raw"].
    The different types of input will always reside inside the input/ directory. However, the files within
    input/ may differ depending on the type of detection being performed. These may look like the following:

        1. eiger4m/lambda2m/rigaku(slow mode) .h5
        2. lambda750k, legacy .imm file. we no longer use it at the beamline.
        3. rigaku500k (fast mode), one .bin file
        4. rigaku3m (fast mode), .bin.xxx file, xxx in [001, ... 006]

    For the last one, the file in boost_corr["raw"] denotes the first of six files, and Corr is smart enough
    to assume the others are present.

    A metadata file almost always exists inside the input/ directory. This file is never referenced directly
    by the flow, but is automatically picked up and run by boost_corr.
    :param boost_corr: A dictionary which MUST contain all required items for running boost_corr,
                       including 'raw', 'qmap' and 'output' at the very least.
    :returns: A dict of metadata describing exceution input variables and execution times
    :raises Exception: If Boost corr failed to run for some reason, including logs that hopefully explain the failure

    """
    import os
    import json
    import time
    import logging
    import subprocess
    import pathlib
    import traceback
    from boost_corr import __version__ as boost_version
    # boost_version = "FAKE TEST VERSION"
    returncode = 0
    # return "TEST"

    try:
        if boost_corr is None and corr_input_file:
            boost_corr = json.loads((pathlib.Path(corr_input_file) / "boost_corr_input.json").read_text())
        # return {
        #     "boost_corr": boost_corr,
        #     "corr_input_file": corr_input_file,
        # }

        # Ensure the output path exists for the corr results file
        pathlib.Path(boost_corr['output']).mkdir(parents=True, exist_ok=True)
        # Set the CWD for Corr. There is no reason for this, it's simply defensive
        # in case corr outputs any file we don't expect.
        os.chdir(boost_corr['output'])

        """
        usage: boost_corr [-h] -r RAW_FILENAME [-q QMAP_FILENAME] [-o OUTPUT_DIR]
                        [-s SMOOTH] [-i GPU_ID] [-nf {0,1}] [-b BEGIN_FRAME]
                        [-e END_FRAME] [-f STRIDE_FRAME] [-a AVG_FRAME] [-t TYPE]
                        [-d DQ_SELECTION] [-v] [-G] [-n] [-np NUM_PARTIAL_G2]
                        [-p PREFIX] [-u SUFFIX] [--bin-time-s BIN_TIME_S]
                        [--run-config-path RUN_CONFIG_PATH] [-w] [-c CONFIG_JSON]

        Compute Multi-tau/Twotime correlation for APS-8IDI XPCS datasets on GPU/CPU

        options:
        -h, --help            show this help message and exit
        -r RAW_FILENAME, --raw RAW_FILENAME Filename of the raw data file (imm/rigaku/hdf)
        -q QMAP_FILENAME, --qmap QMAP_FILENAME Filename of the qmap file (h5/hdf)
        -o OUTPUT_DIR, --output OUTPUT_DIR Output directory for result files. Directory will be created if it doesn't exist. [default: cluster_results]
        -s SMOOTH, --smooth SMOOTH
        Smooth method for Twotime correlation. [default: sqmap]
        -i GPU_ID, --gpu-id GPU_ID GPU selection: -1 for CPU, -2 for auto-scheduling, >=0 for specific GPU. [default: -1]
        -nf {0,1}, --normalize-frame {0,1}
        1 to enable, 0 to disable frame-based normalization.
        [default: True]
        -b BEGIN_FRAME, --begin-frame BEGIN_FRAME
        Starting frame index (0-based) for correlation. Used
        to skip bad initial frames. If negative, it will use
        python slice stype to resolve the start frames.
        [default: 0]
        -e END_FRAME, --end-frame END_FRAME
        Ending frame index (0-based, exclusive) for
        correlation. -1 uses all frames after begin_frame.
        [default: -1]
        -f STRIDE_FRAME, --stride-frame STRIDE_FRAME
        Frame stride for processing. [default: 1]
        -a AVG_FRAME, --avg-frame AVG_FRAME
        Number of frames to average before correlation.
        [default: 1]
        -t TYPE, --type TYPE  Analysis type: "Multitau", "Twotime", or "Both".
        [default: Multitau]
        -d DQ_SELECTION, --dq-selection DQ_SELECTION
        DQ list selection (e.g., "1,2,5-7" selects
        [1,2,5,6,7]). "all" uses all dynamic qindex. [default:
        all]
        -v, --verbose         Enable verbose output
        -G, --save-G2         Save G2, IP, and IF to file
        -n, --dry-run         Show arguments without executing
        -np NUM_PARTIAL_G2, --num-partial-g2 NUM_PARTIAL_G2
        number of partial g2 to compute. if 0, no partial g2
        will be computed
        -p PREFIX, --prefix PREFIX
        prefix to add to the result filename
        -u SUFFIX, --suffix SUFFIX
        suffix to add to the result filename
        --bin-time-s BIN_TIME_S
        time bin size in seconds for Timepix4 data. [default:
        1e-06]
        --run-config-path RUN_CONFIG_PATH
        Path to the run configuration file for Timepix4 data.
        [default: None]
        -w, --overwrite       Overwrite existing result files
        -c CONFIG_JSON, --config CONFIG_JSON
        Configuration file path. Command line arguments
        override config file values
        """


        cmd = [
            "boost_corr",
            "-r", boost_corr["raw"],
            "-q", boost_corr["qmap"],
            "-o", boost_corr["output"],
            "-i", str(boost_corr["gpu_id"]),
            "-s", boost_corr["smooth"],
            "-b", str(boost_corr["begin_frame"]),
            "-e", str(boost_corr["end_frame"]),
            "-f", str(boost_corr["stride_frame"]),
            "-a", str(boost_corr["avg_frame"]),
            "-t", boost_corr["type"],
            "-d", boost_corr["dq_selection"],
            "-G" if boost_corr["save_g2"] else "",
            "-w" if boost_corr["overwrite"] else "",
            "-v" if boost_corr["verbose"] else "",
            f"-p {boost_corr['prefix']}" if boost_corr.get('prefix') else "",
            f"-u {boost_corr['suffix']}" if boost_corr.get('suffix') else "",
            f"-nf {boost_corr['normalize_frame']}" if "normalize_frame" in boost_corr else "",
            f"-p {boost_corr['prefix']}" if boost_corr.get('prefix') else "",
            # "--bin-time-s 0.000001",
        ]
        corr_start = time.time()
        result = subprocess.run([" ".join(cmd)], shell=True, capture_output=True, text=True)
        returncode = result.returncode
        execution_time_seconds = round(time.time() - corr_start, 2)

        log_file = pathlib.Path(boost_corr["output"]) / "boost_corr.log"
        log_file.write_text(str(result.stdout))

        log_file = pathlib.Path(boost_corr["output"]) / "boost_corr_err.log"
        log_file.write_text(str(result.stderr))

        metadata = {
            'tools' : [{
                'name': 'boost_corr',
                'tool_version': str(boost_version),
                'execution_time_seconds': execution_time_seconds,
                'device': 'gpu' if boost_corr.get('gpu_flag', 0) >= 0 else 'cpu',
                'source': 'https://pypi.org/project/boost_corr/',
                }]
        }

        metadata_file = pathlib.Path(boost_corr["output"]) / "corr_metadata_output.json"
        metadata_file_content = {
            'boost_corr': boost_corr,
            'execution_time_seconds': execution_time_seconds,
            'metadata': metadata,
        }
        metadata_file.write_text(json.dumps(metadata_file_content, indent=2))
    except Exception:
        error_log = pathlib.Path(pathlib.Path(boost_corr["output"]) / "globus_compute_error.log")
        error_log.write_text(traceback.format_exc())

    # corr_input_file means we're in 'batch' mode, and we need to return as little metadata as possible
    if corr_input_file:
        return {
            'result': 'SUCCESS' if returncode == 0 else "FAILED",
        }
    else:
        return {
            # 'stdout': str(result.stdout),
            # 'stderr': str(result.stderr),
            'result': 'SUCCESS' if returncode == 0 else "FAILED",
            'metadata': metadata,
            'metadata_file_content': metadata_file_content,
        }


@generate_flow_definition(modifiers={
    xpcs_boost_corr: {
        'WaitTime': 604800,
        'ExceptionOnActionFailure': True,
    }
})
class BoostCorr(GladierBaseTool):
    action_url = "https://compute.actions.globus.org/v3"

    required_input = [
        'boost_corr',
        'compute_endpoint',
    ]

    compute_functions = [
        xpcs_boost_corr
    ]


if __name__ == '__main__':
    data = {
        'proc_dir':'/eagle/APSDataAnalysis/nick/xpcs_gpu/C032_B315_A200_150C_att01_001_0001-1000',
        'boost_corr': {
            'raw':'C032_B315_A200_150C_att01_001_0001-1000/input/C032_B315_A200_150C_att01_001_00001-01000.imm',
            'qmap':'C032_B315_A200_150C_att01_001_0001-1000/qmap/bates202202_qmap_Lq1_ccdz25_S270_D54.h5',
            'verbose':True,
            'atype': 'Both',

            'output': 'C032_B315_A200_150C_att01_001_0001-1000/qmap/',
            'batch_size': 8,
            'gpu_id': 0,
            'verbose': True,
            'masked_ratio_threshold': 0.75,
            'use_loader': True,
            'begin_frame': 1,
            'end_frame': -1,
            'avg_frame': 1,
            'stride_frame': 1,
            'overwrite': False
        }
    }
    from pprint import pprint
    pprint(xpcs_boost_corr(**data))
