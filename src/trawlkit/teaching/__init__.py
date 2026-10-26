"""Modo docente (Fase 17): banco de ejercicios con corrección y laboratorios guiados."""

from trawlkit.teaching.bank import (
    LEVELS,
    ExerciseInstance,
    ExerciseSpec,
    Grade,
    Solution,
    UnknownExerciseError,
    bank,
    exercise,
    grade,
    instantiate,
    load_bank,
    parse_number,
    solve,
)

__all__ = [
    "LEVELS",
    "ExerciseInstance",
    "ExerciseSpec",
    "Grade",
    "Solution",
    "UnknownExerciseError",
    "bank",
    "exercise",
    "grade",
    "instantiate",
    "load_bank",
    "parse_number",
    "solve",
]
