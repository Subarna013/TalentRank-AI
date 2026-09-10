from streamlit_option_menu import option_menu
import streamlit as st

def sidebar():

    with st.sidebar:

        selected = option_menu(
            menu_title="REDROB AI",
            options=[
                "Dashboard",
                "Analytics",
                "Deep Dive",
                "Compare",
                "Export"
            ],
            icons=[
                "house",
                "bar-chart",
                "person",
                "layers",
                "download"
            ],
            default_index=0,
            styles={
                "container":{
                    "padding":"10px",
                    "background-color":"#0B1220",
                },

                "icon":{
                    "color":"#00D4FF",
                    "font-size":"20px",
                },

                "nav-link":{
                    "font-size":"17px",
                    "margin":"6px",
                    "border-radius":"12px",
                    "--hover-color":"#1E293B",
                },

                "nav-link-selected":{
                    "background-color":"#00D4FF",
                    "color":"black",
                    "font-weight":"bold",
                },
            }
        )

    return selected