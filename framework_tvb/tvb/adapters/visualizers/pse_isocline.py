# -*- coding: utf-8 -*-
#
#
# TheVirtualBrain-Framework Package. This package holds all Data Management, and
# Web-UI helpful to run brain-simulations. To use it, you also need do download
# TheVirtualBrain-Scientific Package (for simulators). See content of the
# documentation-folder for more details. See also http://www.thevirtualbrain.org
#
# (c) 2012-2020, Baycrest Centre for Geriatric Care ("Baycrest") and others
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this
# program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#   CITATION:
# When using The Virtual Brain for scientific publications, please cite it as follows:
#
#   Paula Sanz Leon, Stuart A. Knock, M. Marmaduke Woodman, Lia Domide,
#   Jochen Mersmann, Anthony R. McIntosh, Viktor Jirsa (2013)
#       The Virtual Brain: a simulator of primate brain network dynamics.
#   Frontiers in Neuroinformatics (7:10. doi: 10.3389/fninf.2013.00010)
#
#

"""
.. moduleauthor:: Dan Pop <dan.pop@codemart.ro>
.. moduleauthor:: Bogdan Neacsa <bogdan.neacsa@codemart.ro>
"""

import numpy
import json
from tvb.core.adapters.abcadapter import ABCAdapterForm
from tvb.core.adapters.abcdisplayer import ABCDisplayer
from tvb.core.adapters.exceptions import LaunchException
from tvb.core.entities.model.model_datatype import DataTypeGroup
from tvb.core.entities.filters.chain import FilterChain
from tvb.core.entities.transient.pse import PSEGroupModel
from tvb.core.neotraits.forms import TraitDataTypeSelectField
from tvb.core.neotraits.view_model import ViewModel, DataTypeGidAttr


class PSEIsoGroupModel(PSEGroupModel):
    def __init__(self, datatype_group_gid):
        super(PSEIsoGroupModel, self).__init__(datatype_group_gid)
        self.apriori_x = self._prepare_axes(self.get_range1_interval())
        self.apriori_y = self._prepare_axes(self.get_range2_interval())

        self.apriori_data = dict()
        self._fill_apriori_data()

    def _ensure_correct_context_for_launch(self, operation):
        if not operation.has_finished:
            raise LaunchException("Not all operations from this range are complete. Cannot view until then.")

    def _prepare_axes(self, range_interval):
        unique_range_interval = list(set(range_interval))
        if type(unique_range_interval[0]) is str:
            axe_interval = numpy.arange(len(unique_range_interval))
            return axe_interval

        axe_interval = numpy.array(unique_range_interval)
        return axe_interval

    def _fill_apriori_data(self):
        """ Gather apriori data from the operations. Also gather the datatype gid's"""

        # An 2D array of GIDs which is used later to launch overlay for a DataType
        array_2d_shape = (len(self.apriori_x), len(self.apriori_y))
        self.datatypes_gids = numpy.reshape(list(self.get_all_metrics().keys()), array_2d_shape).tolist()

        for metric_key in self.get_available_metric_keys():
            # TODO: check this or numpy.NaN
            metric_values = [metric_value[metric_key] or numpy.NaN for metric_value in
                             list(self.get_all_metrics().values())]
            metric_values = numpy.reshape(metric_values, array_2d_shape)
            self.apriori_data.update({metric_key: metric_values})


class IsoclinePSEAdapterModel(ViewModel):
    datatype_group = DataTypeGidAttr(
        linked_datatype=DataTypeGroup,
        label='Datatype Group'
    )


class IsoclinePSEAdapterForm(ABCAdapterForm):

    def __init__(self, prefix='', project_id=None):
        super(IsoclinePSEAdapterForm, self).__init__(prefix, project_id)
        self.datatype_group = TraitDataTypeSelectField(IsoclinePSEAdapterModel.datatype_group, self,
                                                       name='datatype_group', conditions=self.get_filters())

    @staticmethod
    def get_view_model():
        return IsoclinePSEAdapterModel

    @staticmethod
    def get_required_datatype():
        return DataTypeGroup

    @staticmethod
    def get_input_name():
        return 'datatype_group'

    @staticmethod
    def get_filters():
        return FilterChain(fields=[FilterChain.datatype + ".no_of_ranges"], operations=["=="], values=[2])


class IsoclinePSEAdapter(ABCDisplayer):
    """
    Visualization adapter for Parameter Space Exploration.
    Will be used as a generic visualizer, accessible when input entity is DataTypeGroup.
    Will also be used in Burst as a supplementary navigation layer.
    """

    _ui_name = "Isocline Parameter Space Exploration"
    _ui_subsection = "pse_iso"

    def __init__(self):
        ABCDisplayer.__init__(self)
        self.interp_models = {}
        self.nan_indices = {}

    def get_form_class(self):
        return IsoclinePSEAdapterForm

    def get_required_memory_size(self, view_model):
        # type: (IsoclinePSEAdapterModel) -> int
        """
        Return the required memory to run this algorithm.
        """
        # Don't know how much memory is needed.
        return -1

    def burst_preview(self, view_model):
        # type: (IsoclinePSEAdapterModel) -> dict
        """
        Generate the preview for the burst page.
        """
        return self.launch(view_model)

    def get_metric_matrix(self, datatype_group_gid, selected_metric=None):
        pse_iso = PSEIsoGroupModel(datatype_group_gid)

        if selected_metric is None:
            selected_metric = list(pse_iso.get_available_metric_keys())[0]

        data_matrix = pse_iso.apriori_data[selected_metric]
        data_matrix = numpy.rot90(data_matrix)
        data_matrix = numpy.flipud(data_matrix)
        matrix_data = ABCDisplayer.dump_with_precision(data_matrix.flat)
        matrix_guids = pse_iso.datatypes_gids
        matrix_guids = numpy.rot90(matrix_guids)
        matrix_shape = json.dumps(data_matrix.squeeze().shape)
        x_min = pse_iso.apriori_x[0]
        x_max = pse_iso.apriori_x[-1]
        y_min = pse_iso.apriori_y[0]
        y_max = pse_iso.apriori_y[-1]
        vmin = data_matrix.min()
        vmax = data_matrix.max()
        return dict(matrix_data=matrix_data,
                    matrix_guids=json.dumps(matrix_guids.flatten().tolist()),
                    matrix_shape=matrix_shape,
                    color_metric=selected_metric,
                    xAxisName=pse_iso.get_range1_key(),
                    yAxisName=pse_iso.get_range2_key(),
                    available_metrics=pse_iso.get_available_metric_keys(),
                    x_min=x_min,
                    x_max=x_max,
                    y_min=y_min,
                    y_max=y_max,
                    vmin=vmin,
                    vmax=vmax)

    @staticmethod
    def prepare_node_data(datatype_group_gid):
        pse_iso = PSEIsoGroupModel(datatype_group_gid)
        return pse_iso.get_all_node_info()

    def launch(self, view_model):
        params = self.get_metric_matrix(view_model.datatype_group.hex)
        params["title"] = self._ui_name
        params["canvasName"] = "Interpolated values for PSE metric: "
        params["url_base"] = "/burst/explore/get_metric_matrix/" + view_model.datatype_group.hex
        params["node_info_url"] = "/burst/explore/get_node_matrix/" + view_model.datatype_group.hex
        return self.build_display_result('pse_isocline/view', params,
                                         pages=dict(controlPage="pse_isocline/controls"))
