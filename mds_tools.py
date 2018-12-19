'''
Collection of odds-and-ends - reuseable tools for MDSplus activities.

T. Golfinopoulos
Started on 18 Dec. 2018
'''


def get_sig_node_recursive(n,node_list,include_raw=False, include_off=False) :
    '''
    Search recursively among child nodes of n.
    
    Signature:
        get_sig_node_recursive(n,node_list,include_raw=False, include_off=False) :
    
    Usage:
     top_node=myTree.getNode('path.to.top.node')
     node_list=[]
     get_sig_node_recursive(top_node,node_list) #Default - skip nodes named "raw" in list
     node_list_with_raw=[]
     get_sig_node_recursive(top_node,node_list,include_raw=True) #Include signal nodes named "raw"
     get_sig_node_recursive(top_node,node_list,include_raw=True,include_off=True) #Include signal nodes named "raw", as well as signal nodes that are turned off

    Result:
     node_list is populated with list of all nodes of usage, 'signal'; include_raw named input
     determines whether or not to include nodes named "raw"

    T. Golfinopoulos, 18 Dec. 2018 (original version from summer 2018)
    '''
    for child in n.getChildren() :
        get_sig_node_recursive(child,node_list)
    for sub_node in n.getNodeWild('*') :
        get_sig_node_recursive(sub_node,node_list)
    
    if str(n.getUsage()).lower()=='signal' and (n.isOn() or include_off) and (n.getNodeName().lower() != 'raw' or include_raw) :
        node_list.append(n)
        
def gen_scope(fname,myTree,active_nodes,max_rows=11,scope_height=1000,scope_width=1000,include_smooth=True, num_smooth=100,top_node=None):
    '''
    Generate a dwscope .dat file from list of nodes.
    
    Signature:
        gen_scope(fname,myTree,active_nodes,top_node,max_rows=11,scope_height=1000,scope_width=1000,include_smooth=True, num_smooth=100,top_node=None):
    
    fname=file name of scope.  .dat suffix automatically-appended
    myTree=MDSplus tree
    active_nodes=iterable list of nodes to include in scope
    
    
    max_rows=maximum number of rows in a column in the scope.  Default=11
    scope_height=height of scope, in pixels.  Default=1000
    scope_width=width of scope, in pixels.  Default=1000
    include_smooth=flag of whether or not to smooth signals using smooth1d over num_smooth points (convolve with square window).  Default=True
    num_smooth=if include_smooth is set to True, smooth by this number of samples.  Default=100
    top_node=reference node for active nodes (usually a near parent node).  Should be default node corresponding to nodes in active_nodes list.  Default=default node of tree.
    
    Scope is layed out to fill up a column of max_rows rows, and then to add more columns
     until all nodes are accounted for
    
    T. Golfinopoulos, 18 Dec. 2018 (original version from summer 2018)
    Depends on numpy
    '''
    import numpy as np
    
    tree_name=str(myTree.treename).lower()
    
    #Set default
    if not top_node is None :
        myTree.setDefault(top_node)
    else :
        top_node=myTree.getDefault()
        
    if num_smooth<=0:
        raise ValueError('num_smooth must be >=0; you entered '+str(num_smooth))
    
    fname+='.dat'
    #Open the data file - blow away old file and start fresh
    datFile=open(fname,mode='w')

    n_cols=int(np.ceil(len(active_nodes)/float(max_rows)))
    n_rows=int(np.ceil(len(active_nodes)/float(n_cols)))
    window_head_and_foot=75 #Sum of bounding panels (title panel, file panel, etc.)
    pane_height=int(np.floor((scope_height-window_head_and_foot)/float(n_rows)))

    ###
    #Write header
    ###
    #Store info as dictionary
    scope_info={'geometry':str(scope_width)+'x'+str(scope_height)+'+207+258',
                'title':'"All '+tree_name.upper()+' sigs,"//$shot',
                'icon_name':'"all sigs"',
                'title_event':'dpcs_store_done',
                'print_file':'all_sigs.ps',
                'print_event':'',
                'print_portrait':'0',
                'print_window_title':'0',
                'printer':'lp',
                'font':'-misc-fixed-bold-r-normal--14-130-75-75-c-70-iso8859-1', #Try this font - doesn't throw error on open.  Want bigger.... medium can be replaced with bold
                'columns':str(n_cols)}

    #Only need to write vpane for all but the last column, since last column's width
    #is inferred from plot width
    for i in range(n_cols-1) :
        scope_info['vpane_'+str(i+1)]=str(np.floor((i+1)*scope_width/float(n_cols)))

    #This info follows Scope.global_1_1 after the header
    global_info={'experiment':tree_name,
                 'shot':"current_shot("+tree_name+")",
                 'default_node':str(top_node.getFullPath()),
                 'event':'STREAM'}
                 
    #Write header to file
    for key in scope_info.keys():
        datFile.write('Scope.'+key+': '+scope_info[key]+'\n')

    #Write global values to file
    datFile.write('\n') #Spacer
    for key in global_info.keys():
        datFile.write('Scope.global_1_1.'+key+': '+global_info[key]+'\n')

    #Remaining values needed for each plot:
    #height, x, y, title, label, and...global_defaults?
    sig_idx=0
    for col in range(n_cols):
        #Need to declare how many rows in each column
        datFile.write('\n') #Spacer between plots
        datFile.write('Scope.rows_in_column_'+str(col+1)+': '+str(n_rows))
        
        for row in range(n_rows):
            plot_name='plot_'+str(row+1)+'_'+str(col+1)
            this_node=active_nodes[sig_idx]
            datFile.write('\n') #Spacer between plots
            datFile.write('Scope.'+plot_name+'.height: '+str(pane_height)+'\n')
            #For some reason, the global setting isn't helping for the default node, though it
            #seems to be okay for "experiment" (tree)
            datFile.write('Scope.'+plot_name+'.default_node: '+str(top_node.getFullPath())+'\n')
            datFile.write('Scope.'+plot_name+'.x: dim_of('+str(this_node.getMinPath())+')\n')
            if include_smooth :
                datFile.write('Scope.'+plot_name+'.y: smooth1d('+str(this_node.getMinPath())+','+str(int(num_smooth))+')\n')
            else :
                datFile.write('Scope.'+plot_name+'.y: '+str(this_node.getMinPath())+'\n')
            try :
                #For now, do this the simplistic way: signal node is always
                #calib*amp_node, and the unit of amp_node is always V (volts), and
                #the unit of calib is (hopefully) always something/V, so just
                #excise the last two characters of units
                #this_unit='['+str(this_node.getNode('calib').getData().units_of()).replace(' ','')[:-2]+']' #Get rid of whitespace first
                #No longer true
                this_unit=str(this_node.getNode('calib').getData().units_of()).replace(' ','')
                #Separate at divide by - remove everything to the right of the last divide by
                this_unit='['+'/'.join(this_unit.split('/')[0:-1])+']' #Preserve all divide-by's except last
            except :
                this_unit='' #No unit available
            this_label=str(this_node.getNodeName())+' '+this_unit
            datFile.write('Scope.'+plot_name+'.label: '+this_label+'\n')
            datFile.write('Scope.'+plot_name+'.title: "'+this_label+'"//$shot\n')
            datFile.write('Scope.'+plot_name+'.event: STREAM\n')
            #datFile.write('Scope.'+plot_name+".shot: current_shot("+tree_name+")\n")
            
            #Increment signal counter
            sig_idx+=1

            if sig_idx>=len(active_nodes) :
                break #Completed all available nodes - leave remaining panes blank
            
    #Close file
    datFile.close()
    print(fname+" complete!")
