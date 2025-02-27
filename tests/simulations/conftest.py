# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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

from pathlib import Path

import pytest
from kqcircuits.simulations.empty_simulation import EmptySimulation
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.sonnet.sonnet_export import export_sonnet


@pytest.fixture
def layout():
    """ Return a new pya Layout """
    return pya.Layout()


@pytest.fixture
def empty_simulation(layout):
    """ Return an instance of EmptySimulation """
    return EmptySimulation(layout)


@pytest.fixture
def perform_test_ansys_export_produces_output_files(tmp_path):
    def perform_test_ansys_export_produces_output_implementation(simulation):
        bat_filename = export_ansys([simulation], path=tmp_path)
        assert Path(bat_filename).exists()

    return perform_test_ansys_export_produces_output_implementation


@pytest.fixture
def perform_test_sonnet_export_produces_output_files(tmp_path):
    def perform_test_sonnet_export_produces_output_implementation(simulation):
        son_filename = export_sonnet([simulation], path=tmp_path)[0]
        assert Path(son_filename).exists()

    return perform_test_sonnet_export_produces_output_implementation

