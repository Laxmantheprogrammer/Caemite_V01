from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import AllChem


@dataclass
class Atom:
    element: str
    x: float
    y: float
    z: float


@dataclass
class Molecule:
    name: str
    atoms: list[Atom]


def smiles_to_3d(smiles: str):
    molecule = Chem.MolFromSmiles(smiles)

    if molecule is None:
        raise ValueError("Invalid SMILES.")

    molecule = Chem.AddHs(molecule)

    result = AllChem.EmbedMolecule(
        molecule,
        randomSeed=42
    )

    if result != 0:
        raise RuntimeError(
            "RDKit could not generate a 3D structure."
        )

    result = AllChem.UFFOptimizeMolecule(molecule)

    if result != 0:
        print("Warning: UFF geometry optimization did not converge.")

    return molecule


def rdkit_to_molecule(molecule, name="molecule"):
    conformer = molecule.GetConformer()

    atoms = []

    for atom in molecule.GetAtoms():
        position = conformer.GetAtomPosition(atom.GetIdx())

        atoms.append(
            Atom(
                element=atom.GetSymbol(),
                x=position.x,
                y=position.y,
                z=position.z,
            )
        )

    return Molecule(
        name=name,
        atoms=atoms,
    )


def smiles_to_molecule(smiles: str, name="user_molecule"):
    rdkit_molecule = smiles_to_3d(smiles)

    return rdkit_to_molecule(
        rdkit_molecule,
        name=name,
    )
