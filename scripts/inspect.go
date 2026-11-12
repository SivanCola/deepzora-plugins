package main
import("os";"fmt";"encoding/json";"deepzora/internal/pluginpkg")
func main(){
 p,w,err:=pluginpkg.ParseDir(os.Args[1]);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 json.NewEncoder(os.Stdout).Encode(map[string]any{"manifestName":p.Manifest.Name,"version":p.Manifest.Version,"manifestKind":p.ManifestKind,"counts":p.CapabilitySummary(),"inventory":p.Inventory(),"compatibility":p.Compatibility,"runtime":p.Manifest.Runtime,"warnings":w})
}

