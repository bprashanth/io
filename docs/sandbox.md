# Codex sandboxing

Codex sandboxing happens in two parts 
1. bubblewrap (conatiner). This prevents global read/write 

  |                                folder                                 |    access     
  |-----------------------------------------------------------------------|---------------
  | the working folder (the sheltered folder, or the conversation's empty | read and      
  |  folder)                                                              | write         
  |-----------------------------------------------------------------------|---------------
  | system libs (/usr, /lib, shells, python)                              | read          
  |-----------------------------------------------------------------------|---------------
  | Codex's own package (the runner, its bundled bubblewrap, rg)          | read          
  |-----------------------------------------------------------------------|---------------
  | /tmp                                                                  | write         
  |-----------------------------------------------------------------------|---------------
  | everything else, including home                                       | not in container
  
2. Networking 

* All calls the codex binary itself makes is routed through the proxy
* All commands codex runs are exec'd in the container (bubblewrap)
* The bubblewrap prevents network access for sheltered dirs 
* The bubblewrap does not prevent network access for normal conversations 

