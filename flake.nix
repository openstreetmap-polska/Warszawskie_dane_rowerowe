{
  description = "Warszawskie dane rowerowe";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
  };

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
    in
    {
      devShells."${system}".default =
        let
          pkgs = import nixpkgs { inherit system; };
        in
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

          shellHook = '''';
        };
    };
}
