import streamlit as st
import time, json
import numpy as np
import altair as alt
import pandas as pd
import Robogame as rg
import networkx as nx
from altair import datum

from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt

# set to wide mode
st.set_page_config(layout="wide")

st.title('ZYPYK Dashboard')

# team = st.text_input('Enter team', '1')
#rid = st.selectbox('id of robot for regression ', np.arange(0, 100))

# let's create seven "spots" in the streamlit view for our charts
status = st.empty()
rounds = st.empty()
regVis = st.empty()
predVis = st.empty()
multVis = st.empty()
networkVis = st.empty()
treeVis = st.empty()



# create the game, and mark it as ready
game = rg.Robogame("bob", multiplayer=True)
# game = rg.Robogame("144",server="roboviz.games",port=5000, multiplayer=True)

game.setReady()


# wait for both players to be ready
while(True):
    gametime = game.getGameTime()
    timetogo = gametime['gamestarttime_secs'] - gametime['servertime_secs']

    if ('Error' in gametime):
        status.write("Error"+str(gametime))
        break
    if (timetogo <= 0):
        status.write("Let's go!")
        break
    status.write("waiting to launch... game will start in " + str(int(timetogo)))
    time.sleep(1) # sleep 1 second at a time, wait for the game to start


st.sidebar.title('')

choice = st.sidebar.selectbox(
    'Choose a page to display',
    ('Regression and Parts', 'Tree and Network')
)

if choice == 'Tree and Network':
    ## Tree and Adjacency list ###

    # get the genealogy tree
    tree = game.getTree()

    # adj matrix/list
    def recurse(d):

        id_temp = d.get('id')
        #print(id_temp)
        tmp = []
        try:
            child = d.get('children')
            for i in range(len(child)):
                id_t, ar_t = recurse(child[i])
                tmp.append(id_t)
                # flat_arr.append([id_temp, id_t])

        except:
            print('')

        arr = np.array([id_temp, tmp], dtype=object)
        arr = [id_temp, tmp, '']

        f_arr.append(arr)
        #print(arr)

        return id_temp, arr

    f_arr = []
    recurse(tree)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)

    # issue with streamlit (column widths not changeable in code) so add 3rd 'filler' column
    adj_df = pd.DataFrame(data = np.array(f_arr, dtype=object),  
                      columns = ['id', 'children         ', ''])

    # tree viz
    G = nx.tree_graph(tree)
    fig, ax = plt.subplots(figsize=(15, 10))
    # fig, ax = plt.subplots()
    pos = graphviz_layout(G, prog='dot')
    nx.draw(G, pos=pos, with_labels = True, font_size=9, node_color='#b0caf6', node_size=350, alpha=0.8)

    # display tree viz and adj list
    with treeVis.container():
        st.header('Family Tree')
        st.pyplot(fig)
        st.dataframe(adj_df)

    ### Network ###
    network = game.getNetwork()
    socialnet = nx.node_link_graph(network)
    soc_ar = sorted(socialnet.degree, key=lambda x: x[1], reverse=True)
    gameFrame = pd.DataFrame(soc_ar,columns=['Node','Degree'])


    # net_chart = nxa.draw_networkx(socialnet)
    # edges = net_chart.layer[0]
    # nodes = net_chart.layer[1]

    # brush = alt.selection_interval(encodings=['x','y'])


    # nodes = nodes.encode(
    #     fill = alt.condition(brush,alt.value("red"),alt.value('gray'))
    # ).add_selection(
    #     brush
    # )

    mouse = alt.selection_single(on='mouseover', empty='none')

    bars = alt.Chart(gameFrame).mark_bar().encode(
        x=alt.X("Node:O",sort="-y",title="Robot"),
        y="Degree",
        tooltip=['Node','Degree'],
        color=alt.condition(mouse, alt.ColorValue('red'), alt.ColorValue('#b0caf6'))
    ).transform_window(
        rank = 'rank(Degree)',
        sort=[alt.SortField('Degree', order='descending')]
    ).transform_filter(
        (alt.datum.rank < 30)
    ).configure_axisX(
        labelAngle=0
    ).properties(
        width=800
    ).add_selection(
        mouse
    )

    # net_chart2 = bars

    with networkVis.container():
        st.header('Network-Degrees')
        # st.write(net_chart)
        st.write(bars)


if choice == 'Regression and Parts':
    # run 100 times
    for i in np.arange(0, 101):
        # sleep 6 seconds
    #     for t in np.arange(0,6):
    #         status.write("Seconds to next hack: " + str(6-t))
    #         # rounds.write("Rounds: " + str(i) + "/100")
    #         time.sleep(1)
        time.sleep(6)
        status.write("Current time: " + str(game.getGameTime()['curtime']))
        # small multiples
        # This part need to be run every 6 seconds
        robots = game.getRobotInfo()

        # Copy the original Dataframe and append those 7 quantitative 
        robots_c=robots.copy()
        robots_c['Nanochip Model'] = ''
        robots_c['Axial Piston Model'] = ''
        robots_c['Arakyd Vocabulator Model']=''
        robots_c['Sonoreceptors']=''
        robots_c['Repulsorlift Motor HP']=''
        robots_c['Cranial Uplink Bandwidth']=''
        robots_c['Polarity Sinks']=''
        robots_c['AutoTerrain Tread Count']=''
        robots_c['InfoCore Size']=''
        robots_c['Astrogation Buffer Length']=''

        # Get Hints
        crnt_time = game.getGameTime()['curtime']

        cur_robots = robots_c[robots_c['expires'] > crnt_time + 5]
        next_four = cur_robots.sort_values('expires')[:4]['id']
        next_list = list(next_four)

        game.setRobotInterest(next_list)
        if (i % 3 == 0):
            game.setRobotInterest([])

        hints = game.getHints()
        # get all the hints we've collected
        predHints = game.getAllPredictionHints()
        partHints = game.getAllPartHints()

        # make the time hints into a dataframe
        predhints_df = pd.read_json(json.dumps(predHints),orient='records')

        # selected those robots that our team won, the number here need to be changes depends on which team we are in
        robots_winned=robots_c #[robots_c.winner == int(team)]
        # st.dataframe(robots_winned)

        # Get the ID columns for later usage
        IDs= robots_winned.id

        # Append the feature hints we get to the corresponding row with the same robot id.
        for robot_id in IDs:
            for item in partHints:
                if item['id'] == robot_id:
                    robots_winned.loc[robot_id,item['column']]= item['value']

        chart1=alt.Chart(robots_winned).mark_line().encode(
            alt.X(alt.repeat("column"), type='quantitative'),
            alt.Y(alt.repeat("row"), type='quantitative'),
            tooltip=['Nanochip Model:N', 'Axial Piston Model:N', 'Arakyd Vocabulator Model:N'],
        ).properties(
            width=150,
            height=150
        ).repeat(
            row=['Productivity'],
            column=['InfoCore Size', 'AutoTerrain Tread Count', 'Astrogation Buffer Length','Polarity Sinks'],
        )

        chart2=alt.Chart(robots_winned).mark_line().encode(
            alt.X(alt.repeat("column"), type='quantitative'),
            alt.Y(alt.repeat("row"), type='quantitative'),
            tooltip=['Nanochip Model:N', 'Axial Piston Model:N', 'Arakyd Vocabulator Model:N'],
        ).properties(
            width=150,
            height=150
        ).repeat(
            row=['Productivity'],
            column=['Cranial Uplink Bandwidth','Repulsorlift Motor HP','Sonoreceptors']
        )

        with multVis.container():
            st.dataframe(robots_c)
            st.header('Parts')
            st.altair_chart(chart1 & chart2)
            #st.dataframe(predhints_df)


        ### Regression ###

        # Create a list for those valid Ids that can be used to select the robot we want to recruit
        Ids = list(predhints_df['id'].unique())
        Ids.sort()

        # Create the selection
        selectId = alt.selection_single(
            fields=["id"],init={"id":Ids[0]},name="id",bind=alt.binding_radio(options=Ids, name='id')
        )

        colorCondition =alt.condition(selectId, alt.Color("id:N"),alt.value("lightgrey"))

        # The base chart to surface the data hints already got for each of the robots
        base=alt.Chart(predhints_df).mark_point().encode(
              alt.X("time:Q"), alt.Y("value:Q") #, color='id:N'
        )

        # Create the vertical line to mark the expires
        expires = alt.Chart(robots).mark_rule(color='red').encode(
            alt.X("expires:Q"), 
            tooltip = ['value:Q']
        ) 


        nearest = alt.selection_single(nearest=True, on='mouseover', fields=['value'], empty='none')

        selector = alt.Chart(predhints_df).mark_point().encode(
            y='value:Q',
            x='time:Q',
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            tooltip=['value:Q'],
            color=alt.value('red')
        ).add_selection(
            nearest
        )

        #calculate how many data hints are already generated for each of the robots
        count_df = predhints_df.groupby(['id']).count()

        #Charts is set up to store each of the charts for each of the robots
        Charts={}

        for id in Ids:
            styled = base.transform_filter(
                (datum.id == id)
            )

            expires_line = expires.transform_filter(
                (datum.id == id)
            )

            #'degree' is the used to do the nominal_fit
            if count_df['value'][id] <=6:
                    degree = count_df['value'][id]-1
            elif count_df['value'][id] > 6:
                    degree = 6

    #         nearest = alt.selection_single(nearest=True, on='mouseover', fields=['value'], empty='none')

    #         selector = alt.Chart(styled).mark_point().encode(
    #             y='value:Q',
    #             x='time:Q',
    #             opacity=alt.condition(nearest, alt.value(1), alt.value(0))
    #         ).add_selection(
    #             nearest
    #         )


            polynomial_fit = [
                styled.transform_regression(
                    "time", "value", method="poly", order=degree, as_=["time", str(degree)]
                )
                .mark_line()
                .transform_fold([str(degree)])
                #.encode(alt.Color("degree:N"))
            ]

    #         points = selector.mark_point().encode(
    #             opacity = alt.condition(nearest, alt.value(1), alt.value(0))
    #         )
            #The Charts[id] can be connected with Steamlit with a drop down menu or similar feature that allow viewers to choose which robot they want to see
            Charts[id]=alt.layer(styled, *polynomial_fit, expires_line, selector)

            with regVis.container():
                st.header('Regression')
                col1, col2 = st.columns(2)
                if len(next_list) < 3:
                    st.write('End of list')
                else:
                    col1.subheader(next_list[0])
                    col1.write(Charts.get(next_list[0]))
                    col1.subheader(next_list[2])
                    col1.write(Charts.get(next_list[2]))
                    col2.subheader(next_list[1])
                    col2.write(Charts.get(next_list[1]))
                    col2.subheader(next_list[3])
                    col2.write(Charts.get(next_list[3]))

        time.sleep(6)
