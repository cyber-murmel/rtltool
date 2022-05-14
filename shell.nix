{
  # nixpkgs 21.11, deterministic. Last updated: 2022-01-01.
  pkgs ? import (fetchTarball("https://github.com/NixOS/nixpkgs/archive/8a053bc.tar.gz")) {}
}:

with pkgs;
let
  my-python-packages = python-packages: with python-packages; [
    pyserial
    crccheck
    coloredlogs
    black
  ];
  python-with-my-packages = python3.withPackages my-python-packages;
in
mkShell {
  buildInputs = [
    python-with-my-packages
  ];
}
