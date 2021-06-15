"""Core makers for running VASP calculations."""

from __future__ import annotations

import logging
import typing
from dataclasses import dataclass, field

from jobflow import Flow, Maker, Response, job
from monty.shutil import gzip_dir

from atomate2.vasp.drones import VaspDrone
from atomate2.vasp.file import copy_vasp_outputs
from atomate2.vasp.inputs import write_vasp_input_set
from atomate2.vasp.makers.base import BaseVaspMaker
from atomate2.vasp.run import run_vasp, should_stop_children
from atomate2.vasp.schemas.task import TaskDocument

if typing.TYPE_CHECKING:
    from pathlib import Path
    from typing import Union

    from pymatgen.core.structure import Structure

logger = logging.getLogger(__name__)


@dataclass
class StaticMaker(BaseVaspMaker):
    """Maker to create VASP static makers."""

    name: str = "static"
    input_set: str = "MPStaticSet"
    input_set_kwargs: dict = field(default_factory=dict)
    write_vasp_input_set_kwargs: dict = field(default_factory=dict)
    copy_vasp_kwargs: dict = field(default_factory=dict)
    run_vasp_kwargs: dict = field(default_factory=dict)
    vasp_drone_kwargs: dict = field(default_factory=dict)
    stop_children_kwargs: dict = field(default_factory=dict)

    @job(output_schema=TaskDocument)
    def make(self, structure: Structure, prev_vasp_dir: Union[str, Path] = None):
        """
        Run a static VASP calculation.

        Parameters
        ----------
        structure
            A pymatgen structure object.
        prev_vasp_dir
            A previous VASP calculation directory to copy output files from.
        """
        # copy previous inputs
        from_prev = prev_vasp_dir is not None
        if prev_vasp_dir is not None:
            copy_vasp_outputs(prev_vasp_dir, **self.copy_vasp_kwargs)

        if "from_prev" not in self.write_vasp_input_set_kwargs:
            self.write_vasp_input_set_kwargs["from_prev"] = from_prev

        # write vasp input files
        write_vasp_input_set(
            structure,
            self.input_set,
            self.input_set_kwargs,
            **self.write_vasp_input_set_kwargs
        )

        # run vasp
        run_vasp(**self.run_vasp_kwargs)

        # parse vasp outputs
        drone = VaspDrone(**self.vasp_drone_kwargs)
        task_doc = drone.assimilate()
        task_doc.task_label = self.name

        # decide whether child makers should proceed
        stop_children = should_stop_children(task_doc, **self.stop_children_kwargs)

        # gzip folder
        gzip_dir(".")

        return Response(
            stop_children=stop_children,
            stored_data={"custodian": task_doc.custodian},
            output=task_doc,
        )


@dataclass
class RelaxMaker(BaseVaspMaker):
    """Maker to create VASP relaxation makers."""

    name: str = "relax"
    input_set: str = "MPRelaxSet"
    input_set_kwargs: dict = field(default_factory=dict)
    write_vasp_input_set_kwargs: dict = field(default_factory=dict)
    copy_vasp_kwargs: dict = field(default_factory=dict)
    run_vasp_kwargs: dict = field(default_factory=dict)
    vasp_drone_kwargs: dict = field(default_factory=dict)
    stop_children_kwargs: dict = field(default_factory=dict)

    @job(output_schema=TaskDocument)
    def make(self, structure: Structure, prev_vasp_dir: Union[str, Path] = None):
        """
        Run an optimization VASP calculation.

        Parameters
        ----------
        structure
            A pymatgen structure object.
        prev_vasp_dir
            A previous VASP calculation directory to copy output files from.
        """
        # copy previous inputs
        from_prev = prev_vasp_dir is not None
        if prev_vasp_dir is not None:
            copy_vasp_outputs(prev_vasp_dir, **self.copy_vasp_kwargs)

        if "from_prev" not in self.write_vasp_input_set_kwargs:
            self.write_vasp_input_set_kwargs["from_prev"] = from_prev

        # write vasp input files
        write_vasp_input_set(
            structure,
            self.input_set,
            self.input_set_kwargs,
            **self.write_vasp_input_set_kwargs
        )

        # run vasp
        run_vasp(**self.run_vasp_kwargs)

        # parse vasp outputs
        drone = VaspDrone(**self.vasp_drone_kwargs)
        task_doc = drone.assimilate()
        task_doc.task_label = self.name

        # decide whether child makers should proceed
        stop_children = should_stop_children(task_doc, **self.stop_children_kwargs)

        # gzip folder
        gzip_dir(".")

        return Response(
            stop_children=stop_children,
            stored_data={"custodian": task_doc.custodian},
            output=task_doc,
        )


@dataclass
class NonSCFMaker(BaseVaspMaker):
    """Maker to create non self consistent field VASP makers."""

    name: str = "non-scf"
    input_set: str = "MPNonSCFSet"
    input_set_kwargs: dict = field(default_factory=dict)
    write_vasp_input_set_kwargs: dict = field(default_factory=dict)
    copy_vasp_kwargs: dict = field(default_factory=dict)
    run_vasp_kwargs: dict = field(default_factory=dict)
    vasp_drone_kwargs: dict = field(default_factory=dict)
    stop_children_kwargs: dict = field(default_factory=dict)

    @job(output_schema=TaskDocument)
    def make(
        self,
        structure: Structure,
        prev_vasp_dir: Union[str, Path],
        mode: str = "uniform",
    ):
        """
        Run a non-scf VASP job.

        Parameters
        ----------
        structure
            A pymatgen structure object.
        prev_vasp_dir
            A previous VASP calculation directory to copy output files from.
        mode
            Type of band structure calculation. Options are:
            - "line": Full band structure along symmetry lines.
            - "uniform": Uniform mesh band structure.
        """
        # copy previous inputs
        if "additional_vasp_files" not in self.copy_vasp_kwargs:
            self.copy_vasp_kwargs["additional_vasp_files"] = ("CHGCAR",)

        copy_vasp_outputs(prev_vasp_dir, **self.copy_vasp_kwargs)

        if "from_prev" not in self.write_vasp_input_set_kwargs:
            self.write_vasp_input_set_kwargs["from_prev"] = True

        if "mode" not in self.input_set_kwargs:
            self.input_set_kwargs["mode"] = mode

        # write vasp input files
        write_vasp_input_set(
            structure,
            self.input_set,
            self.input_set_kwargs,
            **self.write_vasp_input_set_kwargs
        )

        # run vasp
        run_vasp(**self.run_vasp_kwargs)

        if "parse_dos" not in self.vasp_drone_kwargs:
            # parse DOS only for uniform band structure
            self.vasp_drone_kwargs["parse_dos"] = mode == "uniform"

        if "parse_bandstructure" not in self.vasp_drone_kwargs:
            self.vasp_drone_kwargs["parse_bandstructure"] = mode

        # parse vasp outputs
        drone = VaspDrone(**self.vasp_drone_kwargs)
        task_doc = drone.assimilate()
        task_doc.task_label = self.name

        # decide whether child makers should proceed
        stop_children = should_stop_children(task_doc, **self.stop_children_kwargs)

        # gzip folder
        gzip_dir(".")

        return Response(
            stop_children=stop_children,
            stored_data={"custodian": task_doc.custodian},
            output=task_doc,
        )


@dataclass
class DFPTMaker(BaseVaspMaker):
    """Maker to create DFPT VASP makers."""

    name: str = "dfpt"
    input_set: str = "MPStaticSet"
    input_set_kwargs: dict = field(default_factory=dict)
    write_vasp_input_set_kwargs: dict = field(default_factory=dict)
    copy_vasp_kwargs: dict = field(default_factory=dict)
    run_vasp_kwargs: dict = field(default_factory=dict)
    vasp_drone_kwargs: dict = field(default_factory=dict)
    stop_children_kwargs: dict = field(default_factory=dict)

    @job(output_schema=TaskDocument)
    def make(self, structure: Structure, prev_vasp_dir: Union[str, Path] = None):
        """
        Run a DFPT VASP job.

        Parameters
        ----------
        structure
            A pymatgen structure object.
        prev_vasp_dir
            A previous VASP calculation directory to copy output files from.
        """
        # copy previous inputs
        from_prev = prev_vasp_dir is not None
        if prev_vasp_dir is not None:
            copy_vasp_outputs(prev_vasp_dir, **self.copy_vasp_kwargs)

        if "from_prev" not in self.write_vasp_input_set_kwargs:
            self.write_vasp_input_set_kwargs["from_prev"] = from_prev

        if "lepsilon" not in self.input_set_kwargs:
            self.input_set_kwargs["lepsilon"] = True

        # write vasp input files
        write_vasp_input_set(
            structure,
            self.input_set,
            self.input_set_kwargs,
            **self.write_vasp_input_set_kwargs
        )

        # run vasp
        run_vasp(**self.run_vasp_kwargs)

        # parse vasp outputs
        drone = VaspDrone(**self.vasp_drone_kwargs)
        task_doc = drone.assimilate()
        task_doc.task_label = self.name

        # decide whether child makers should proceed
        stop_children = should_stop_children(task_doc, **self.stop_children_kwargs)

        # gzip folder
        gzip_dir(".")

        return Response(
            stop_children=stop_children,
            stored_data={"custodian": task_doc.custodian},
            output=task_doc,
        )


@dataclass
class HSEBSMaker(BaseVaspMaker):
    """Maker to create DFPT VASP makers."""

    name: str = "hse band structure"
    input_set: str = "MPHSEBSSet"
    input_set_kwargs: dict = field(default_factory=dict)
    write_vasp_input_set_kwargs: dict = field(default_factory=dict)
    copy_vasp_kwargs: dict = field(default_factory=dict)
    run_vasp_kwargs: dict = field(default_factory=dict)
    vasp_drone_kwargs: dict = field(default_factory=dict)
    stop_children_kwargs: dict = field(default_factory=dict)

    @job(output_schema=TaskDocument)
    def make(
        self,
        structure: Structure,
        prev_vasp_dir: Union[str, Path] = None,
        mode="uniform",
    ):
        """
        Run a HSE06 band structure VASP job.

        Parameters
        ----------
        structure
            A pymatgen structure object.
        prev_vasp_dir
            A previous VASP calculation directory to copy output files from.
        mode
            Type of band structure calculation. Options are:
            - "line": Full band structure along symmetry lines.
            - "uniform": Uniform mesh band structure.
            - "gap": Get the energy at the CBM and VBM.
        """
        if mode == "gap" and prev_vasp_dir is None:
            logger.warning(
                "HSE band structure in 'gap' mode requires a previous VASP calculation "
                "directory from which to extract the VBM and CBM k-points. This "
                "calculation will instead be a standard uniform calculation."
            )

        # copy previous inputs
        from_prev = prev_vasp_dir is not None
        if prev_vasp_dir is not None:
            if "additional_vasp_files" not in self.copy_vasp_kwargs:
                self.copy_vasp_kwargs["additional_vasp_files"] = ("CHGCAR",)
            copy_vasp_outputs(prev_vasp_dir, **self.copy_vasp_kwargs)

        if "from_prev" not in self.write_vasp_input_set_kwargs:
            self.write_vasp_input_set_kwargs["from_prev"] = from_prev

        if "lepsilon" not in self.input_set_kwargs:
            self.input_set_kwargs["lepsilon"] = True

        # write vasp input files
        write_vasp_input_set(
            structure,
            self.input_set,
            self.input_set_kwargs,
            **self.write_vasp_input_set_kwargs
        )

        # run vasp
        run_vasp(**self.run_vasp_kwargs)

        if "parse_dos" not in self.vasp_drone_kwargs:
            # parse DOS only for uniform band structure
            self.vasp_drone_kwargs["parse_dos"] = mode == "uniform"

        if "parse_bandstructure" not in self.vasp_drone_kwargs:
            parse_bandstructure = "uniform" if mode == "gap" else mode
            self.vasp_drone_kwargs["parse_bandstructure"] = parse_bandstructure

        # parse vasp outputs
        drone = VaspDrone(**self.vasp_drone_kwargs)
        task_doc = drone.assimilate()
        task_doc.task_label = self.name

        # decide whether child makers should proceed
        stop_children = should_stop_children(task_doc, **self.stop_children_kwargs)

        # gzip folder
        gzip_dir(".")

        return Response(
            stop_children=stop_children,
            stored_data={"custodian": task_doc.custodian},
            output=task_doc,
        )


@dataclass
class DoubleRelaxMaker(Maker):
    """Maker to perform a double VASP relaxation."""

    name: str = "double relax"
    relax_maker: BaseVaspMaker = field(default_factory=RelaxMaker)

    def make(self, structure: Structure, prev_vasp_dir: Union[str, Path] = None):
        """
        Create a flow with two chained relaxations.

        Parameters
        ----------
        structure
            A pymatgen structure object.
        prev_vasp_dir
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing two relaxations.
        """
        relax1 = self.relax_maker.make(structure, prev_vasp_dir=prev_vasp_dir)
        relax1.name += " 1"

        relax2 = self.relax_maker.make(
            relax1.output.structure, prev_vasp_dir=relax1.output.dir_name
        )
        relax2.name += " 2"

        return Flow([relax1, relax2], relax2.output, name=self.name)