{ pkgs ? import <nixpkgs> {} }:
  pkgs.mkShell {
  packages = with pkgs; [
    gdal
    just
    python311
    keep-sorted
    uv
  ];
  env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.stdenv.cc.cc.lib
    pkgs.libz
  ];
}
