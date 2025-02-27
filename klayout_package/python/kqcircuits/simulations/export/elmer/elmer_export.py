# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import os
import stat
import logging
import json

from pathlib import Path
from distutils.dir_util import copy_tree

from kqcircuits.simulations.export.util import export_layers
from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.defaults import ELMER_SCRIPT_PATHS, default_layers
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder

default_gmsh_params = {
    'default_mesh_size': 100,  # Default size to be used where not defined
    'signal_min_mesh_size': 100,  # Minimum mesh size near signal region curves
    'signal_min_dist': 100,  # Mesh size will be the minimum size until this distance from the signal region curves
    'signal_max_dist': 100,  # Mesh size will grow from to the maximum size until this distance from the signal region
                             # curves
    'signal_sampling': None,  # Number of points used for sampling each signal region curve
    'ground_min_mesh_size': 100,  # Minimum mesh size near ground region curves
    'ground_min_dist': 100,  # Mesh size will be the minimum size until this distance from the ground region curves
    'ground_max_dist': 100,  # Mesh size will grow from to the maximum size until this distance from the ground region
                             # curves
    'ground_sampling': None,  # Number of points used for sampling each ground region curve
    'ground_grid_min_mesh_size': 100,  # Minimum mesh size near ground_grid region curves
    'ground_grid_min_dist': 100,  # Mesh size will be the minimum size until this distance from the ground_grid region
                                  # curves
    'ground_grid_max_dist': 100,  # Mesh size will grow from to the maximum size until this distance from the ground_
                                  # grid region curves
    'ground_grid_sampling': None,  # Number of points used for sampling each ground_grid region curve
    'gap_min_mesh_size': 100,  # Minimum mesh size near gap region curves
    'gap_min_dist': 100,  # Mesh size will be the minimum size until this distance from the gap region curves
    'gap_max_dist': 100,  # Mesh size will grow from to the maximum size until this distance from the gap region curves
    'gap_sampling': None,  # Number of points used for sampling each gap region curve
    'port_min_mesh_size': 100,  # Minimum mesh size near port region curves
    'port_min_dist': 100,  # Mesh size will be the minimum size until this distance from the port region curves
    'port_max_dist': 100,  # Mesh size will grow from to the maximum size until this distance from the port region
                           # curves
    'port_sampling': None,  # Number of points used for sampling each port region curve
    'algorithm': 5,  # Gmsh meshing algorithm (default is 5)
}

default_workflow = {
    'run_gmsh': True,  # Run Gmsh to generate mesh
    'run_gmsh_gui': False,  # Show the mesh in Gmsh graphical interface after completing the mesh
    'run_elmergrid': True,  # Run ElmerGrid
    'run_elmer': True,  # Run Elmer simulation
    'run_paraview': False,  # Run Paraview. This is visual view of the results.
    'gmsh_n_threads': 1,  # number of threads used in Gmsh meshing (default=1, -1 means all physical cores)
    'elmer_n_processes': 1,  # number of processes used in Elmer simulation (default=1, -1 means all physical cores)
    'python_executable': 'python' # the python executable that is used to prepare and control the simulations
                                  # another executable could be 'kqclib' (in case the singularity image is used
                                  # the host system python is at the same time needed and does not have all the
                                  # libraries installed for running the simulations)
}


def copy_elmer_scripts_to_directory(path: Path):
    """
    Copies Elmer scripts into directory path.

    Args:
        path: Location where to copy scripts folder.
    """
    if path.exists() and path.is_dir():
        for script_path in ELMER_SCRIPT_PATHS:
            copy_tree(str(script_path), str(path), update=1)


def export_elmer_json(simulation: Simulation, path: Path, tool='capacitance',
                      frequency=5, gmsh_params=None, workflow=None):
    """
    Export Elmer simulation into json and gds files.

    Args:
        simulation: The simulation to be exported.
        path: Location where to write json.
        tool(str): Available: "capacitance" and "wave_equation" (Default: capacitance)
        frequency: Units are in GHz. To set up multifrequency analysis, use list of numbers.
        gmsh_params(dict): Parameters for Gmsh
        workflow(dict): Parameters for simulation workflow

    Returns:
         Path to exported json file.
    """
    if simulation is None or not isinstance(simulation, Simulation):
        raise ValueError("Cannot export without simulation")

    # select layers
    layers = ["1t1_simulation_signal",
              "1t1_simulation_ground",
              "1t1_simulation_gap",
              "1t1_ground_grid"]
    if simulation.wafer_stack_type == "multiface":
        layers += ["2b1_simulation_signal",
                   "2b1_simulation_ground",
                   "2b1_simulation_gap",
                   "2b1_ground_grid"]

    # collect data for .json file
    json_data = {
        'tool': tool,
        **simulation.get_simulation_data(),
        'layers': {r: (default_layers[r].layer, default_layers[r].datatype) for r in layers},
        'gmsh_params': default_gmsh_params if gmsh_params is None else {**default_gmsh_params, **gmsh_params},
        'workflow': default_workflow if workflow is None else {**default_workflow, **workflow},
        'frequency': frequency,
    }

    # write .json file
    json_filename = str(path.joinpath(f'{simulation.name}.json'))
    with open(json_filename, 'w') as fp:
        json.dump(json_data, fp, cls=GeometryJsonEncoder, indent=4)

    # write .gds file
    gds_filename = str(path.joinpath(f'{simulation.name}.gds'))
    export_layers(gds_filename, simulation.layout, [simulation.cell], output_format='GDS2',
                  layers={default_layers[r] for r in layers})

    return json_filename


def export_elmer_script(json_filenames, path: Path, workflow=None, file_prefix='simulation',
        script_file='scripts/run.py'):
    """
    Create script files for running one or more simulations.
    Create also a main script to launch all the simulations at once.

    Args:
        json_filenames: List of paths to json files to be included into the script.
        path: Location where to write the script file.
        workflow(dict): Parameters for simulation workflow
        file_prefix: Name of the script file to be created.
        script_file: Name of the script file to run.

    Returns:

        Path of exported main script file
    """
    if workflow is None:
        workflow = {}
    sbatch = 'sbatch_parameters' in workflow
    if sbatch:
        sbatch_parameters = workflow['sbatch_parameters']
        elmer_n_processes = sbatch_parameters['--ntasks']
    python_executable = workflow.get('python_executable', 'python')
    parallelize_workload = 'n_workers' in workflow


    main_script_filename = str(path.joinpath(f'{file_prefix}.sh'))
    with open(main_script_filename, 'w') as main_file:

        if parallelize_workload and not sbatch:
            main_file.write(
                f"{python_executable} scripts/simple_workload_manager.py {workflow['n_workers']}"
            )

        script_filenames = []
        for i, json_filename in enumerate(json_filenames):
            with open(json_filename) as f:
                json_data = json.load(f)
                simulation_name = json_data['parameters']['name']
            script_filename = str(path.joinpath(f'{simulation_name}.sh'))
            script_filenames.append(script_filename)
            with open(script_filename, 'w') as file:
                if sbatch:
                    file.write('#!/bin/bash\n')
                    file.write(f"#SBATCH --job-name={sbatch_parameters['--job-name']}_{str(i)}\n")
                    file.write(f"#SBATCH --account={sbatch_parameters['--account']}\n")
                    file.write(f"#SBATCH --partition={sbatch_parameters['--partition']}\n")
                    file.write(f"#SBATCH --time={sbatch_parameters['--time']}\n")
                    file.write(f'#SBATCH --ntasks={elmer_n_processes}\n')
                    file.write(f"#SBATCH --cpus-per-task={sbatch_parameters['--cpus-per-task']}\n")
                    file.write(f"#SBATCH --mem-per-cpu={sbatch_parameters['--mem-per-cpu']}\n")
                    file.write('\n')
                    file.write('# set the number of threads based on --cpus-per-task\n')
                    file.write('export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK\n')
                    file.write('\n')
                    file.write(f'echo "Simulation {i + 1}/{len(json_filenames)} Gmsh"\n')
                    file.write('srun -n 1 {2} "{0}" "{1}" --only-gmsh -q 2>&1 >> "{1}_Gmsh.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                        )
                    file.write(f'echo "Simulation {i + 1}/{len(json_filenames)} ElmerGrid"\n')
                    file.write(
                        'ElmerGrid 14 2 "{0}" 2>&1 >> "{1}_ElmerGrid.log"\n'.format(
                            f"{simulation_name}.msh",
                            Path(json_filename).relative_to(path),
                        )
                    )
                    file.write('ElmerGrid 2 2 "{0}" 2>&1 -metis {1} 4 --partdual --removeunused >> '\
                            '"{2}_ElmerGrid_part.log"\n'.format(
                        simulation_name,
                        str(elmer_n_processes),
                        Path(json_filename).relative_to(path))
                    )

                    file.write(f'echo "Simulation {i + 1}/{len(json_filenames)} Elmer"\n')
                    file.write(
                        f'srun --cpu-bind none -n {elmer_n_processes} ElmerSolver_mpi "sif/{simulation_name}.sif" 2>&1 >> "{Path(json_filename).relative_to(path)}_Elmer.log"\n'
                    )
                    file.write(
                        f'echo "Simulation {i + 1}/{len(json_filenames)} write results json"\n'
                    )
                    file.write('srun -n 1 {2} "{0}" "{1}" --write-project-results 2>&1 >> '\
                            '{1}_write_project_results.log\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                else:
                    file.write(f'echo "Simulation {i + 1}/{len(json_filenames)} Gmsh"\n')
                    file.write('{2} "{0}" "{1}" --only-gmsh 2>&1 >> "{1}_Gmsh.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                    file.write(f'echo "Simulation {i + 1}/{len(json_filenames)} ElmerGrid"\n')
                    file.write('{2} "{0}" "{1}" --only-elmergrid 2>&1 >> "{1}_ElmerGrid.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                    file.write(f'echo "Simulation {i + 1}/{len(json_filenames)} Elmer"\n')
                    file.write('{2} "{0}" "{1}" --only-elmer 2>&1 >> "{1}_Elmer.log"\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )
                    file.write(f'echo "Simulation {i + 1}/{len(json_filenames)} Paraview"\n')
                    file.write('{2} "{0}" "{1}" --only-paraview\n'.format(
                        script_file,
                        Path(json_filename).relative_to(path),
                        python_executable)
                    )

            # change permission
            os.chmod(script_filename, os.stat(script_filename).st_mode | stat.S_IEXEC)

            if sbatch:
                main_file.write(
                    f'echo "Submitting the main script of simulation {i + 1}/{len(json_filenames)}"\n'
                )
                main_file.write('echo "--------------------------------------------"\n')
                main_file.write(f'sbatch "{Path(script_filename).relative_to(path)}"\n')
            elif parallelize_workload:
                main_file.write(f' "./{Path(script_filename).relative_to(path)}"')
            else:
                main_file.write(
                    f'echo "Submitting the main script of simulation {i + 1}/{len(json_filenames)}"\n'
                )
                main_file.write('echo "--------------------------------------------"\n')
                main_file.write(f'"./{Path(script_filename).relative_to(path)}"\n')


    # change permission
    os.chmod(main_script_filename, os.stat(main_script_filename).st_mode | stat.S_IEXEC)

    return main_script_filename


def export_elmer(simulations: [], path: Path, tool='capacitance', frequency=5, file_prefix='simulation',
                 script_file='scripts/run.py', gmsh_params=None, workflow=None, skip_errors=False):
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        simulations(list(Simulation)): list of all the simulations
        path(Path): Location where to output the simulation model
        tool(str): Available: "capacitance" and "wave_equation" (Default: capacitance)
        frequency: Units are in GHz. To set up multifrequency analysis, use list of numbers.
        file_prefix: File prefix of the script file to be created.
        script_file: Name of the script file to run.
        gmsh_params(dict): Parameters for Gmsh
        workflow(dict): Parameters for simulation workflow
        skip_errors(bool): Skip simulations that cause errors. (Default: False)

            .. warning::

               **Use this carefully**, some of your simulations might not make sense physically and
               you might end up wasting time on bad simulations.

    Returns:

        Path to exported script file.
    """
    write_commit_reference_file(path)
    copy_elmer_scripts_to_directory(path)
    json_filenames = []
    for simulation in simulations:
        try:
            json_filenames.append(export_elmer_json(simulation, path, tool, frequency, gmsh_params, workflow))
        except Exception as e:
            if skip_errors:
                logging.warning(
                    f'Simulation {simulation.name} skipped due to {e.args}. '\
                    'Some of your other simulations might not make sense geometrically. '\
                    'Disable `skip_errors` to see the full traceback.'
                )
            else:
                raise UserWarning(
                    'Generating simulation failed. You can discard the errors using `skip_errors` in `export_elmer`. '\
                    'Moreover, `skip_errors` enables visual inspection of failed and successful simulation '\
                    'geometry files.'
                ) from e

    return export_elmer_script(json_filenames, path, workflow, file_prefix=file_prefix, script_file=script_file)
