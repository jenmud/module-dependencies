# Modules indepth directed dependency graph 
Generate a indepth directed dependency graph for a module.

# Install
```bash
$ pip install funnel-web
```

# Scraping
```bash
$ funnel-web funnel_web
INFO:root:Vertices: 1011
INFO:root:Edges: 3974
INFO:root:Modules: 46
INFO:root:Classes: 267
INFO:root:Methods: 299
INFO:root:Function: 348
INFO:root:Files: 51
INFO:root:Starting server 0.0.0.0:8000
INFO:ruruki_eye.server:Setting up db to <ruruki.graphs.Graph object at 0x10e7ff450>
INFO:werkzeug: * Running on http://0.0.0.0:8000/ (Press CTRL+C to quit)
```

# Extra args
```bash
$ funnel-web --help
usage: funnel-web [-h] [--address ADDRESS] [--port PORT]
                  [--level {info,warn,error,debug}] [--logfile LOGFILE]
                  module

Generate an indepth directed dependency graph for a given module.

positional arguments:
  module                Importable module to inspect.

optional arguments:
  -h, --help            show this help message and exit
  --address ADDRESS     Address to bind to.
  --port PORT           Port for ruruki-eye to listen on.
  --level {info,warn,error,debug}
                        Logging level.
  --logfile LOGFILE     Send logs to a file. Default is to log to stdout.
```

![Screenshot](/funnel-web.png)
