from molecule import Molecule, smiles_to_molecule
import subprocess


PSEUDO_DIR = "/home/laxma/QE_src/q-e/QEHeat/examples/pseudo"

QE_PATH = "/home/laxma/QE_src/q-e/build/bin/pw.x"


PSEUDOPOTENTIALS = {
    "H": ("1.008", "H_HSCV_PBE-1.0.upf"),
    "O": ("15.999", "O_HSCV_PBE-1.0.upf"),
    "Ar": ("39.948", "Ar_ONCV_PBE-1.0.upf"),
    "Si": ("28.085", "Si_ONCV_PBE-1.1.upf"),
}


def generate_qe_input(molecule: Molecule) -> str:

    elements = []

    for atom in molecule.atoms:
        if atom.element not in elements:
            elements.append(atom.element)

    # Make sure we have pseudopotentials for every element.
    for element in elements:
        if element not in PSEUDOPOTENTIALS:
            raise ValueError(
                f"No pseudopotential configured for element: {element}"
            )

    qe = "&CONTROL\n"
    qe += "    calculation = 'scf',\n"
    qe += "    prefix = 'caemite',\n"
    qe += f"    pseudo_dir = '{PSEUDO_DIR}',\n"
    qe += "    tprnfor = .true.,\n"
    qe += "/\n"

    qe += "&SYSTEM\n"
    qe += "    ibrav = 0,\n"
    qe += f"    nat = {len(molecule.atoms)},\n"
    qe += f"    ntyp = {len(elements)},\n"
    qe += "    ecutwfc = 50,\n"
    qe += "/\n"

    qe += "&ELECTRONS\n"
    qe += "    conv_thr = 1.0d-8,\n"
    qe += "/\n"

    qe += "ATOMIC_SPECIES\n"

    for element in elements:
        mass, pseudopotential = PSEUDOPOTENTIALS[element]

        qe += (
            f"    {element}  {mass}  "
            f"{pseudopotential}\n"
        )

    qe += "\nATOMIC_POSITIONS angstrom\n"

    for atom in molecule.atoms:
        qe += (
            f"    {atom.element} "
            f"{atom.x:.8f} "
            f"{atom.y:.8f} "
            f"{atom.z:.8f}\n"
        )

    qe += "\nCELL_PARAMETERS angstrom\n"
    qe += "    10.0  0.0   0.0\n"
    qe += "    0.0   10.0  0.0\n"
    qe += "    0.0   0.0  10.0\n"

    qe += "\nK_POINTS gamma\n"

    return qe

def parse_forces(output_file):

    forces = []

    with open(output_file) as f:
        for line in f:
            if line.strip().startswith("atom") and "force =" in line:
                parts = line.split()

                fx = float(parts[6])
                fy = float(parts[7])
                fz = float(parts[8])

                forces.append((fx, fy, fz))

    return forces


def run_qe(molecule: Molecule):

    qe_input = generate_qe_input(molecule)

    input_file = "caemite.scf.in"
    output_file = "caemite.scf.out"

    with open(input_file, "w") as f:
        f.write(qe_input)

    print("\nRunning Quantum ESPRESSO...")

    with open(output_file, "w") as output:

        subprocess.run(
            [QE_PATH],
            stdin=open(input_file),
            stdout=output,
            stderr=subprocess.STDOUT,
            check=True,
        )

    print("QE calculation finished.")
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    forces = parse_forces(output_file)

    print("\nForces:")
    for i, force in enumerate(forces, start=1):
        print(f"Atom {i}: {force}")

def main():

    smiles = input("Enter SMILES: ")

    molecule = smiles_to_molecule(
        smiles,
        name="user_molecule"
    )

    print("\nSuccessfully generated 3D molecule!")
    print("Number of atoms:", len(molecule.atoms))

    print("\nAtomic coordinates:")

    for atom in molecule.atoms:

        print(
            f"{atom.element:2s} "
            f"{atom.x:10.5f} "
            f"{atom.y:10.5f} "
            f"{atom.z:10.5f}"
        )

    run_qe(molecule)


if __name__ == "__main__":
    main()
