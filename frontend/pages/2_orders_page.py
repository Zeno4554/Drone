"""Orders page - Place orders and track delivery."""

import streamlit as st
import pandas as pd
from datetime import datetime
from frontend.services.api_client import APIClient


def show(api_url: str):
    """Display orders page."""
    st.title("📦 Order Management")
    
    api = APIClient(api_url)
    
    tab1, tab2, tab3 = st.tabs(["📝 Place Order", "🚚 Active Orders", "📋 Order History"])
    
    # Tab 1 - Place Order
    with tab1:
        st.subheader("Place New Order")
        
        col1, col2 = st.columns(2)
        
        with col1:
            buildings = api.get_buildings()
            if not buildings:
                st.error("Failed to load buildings. Is the backend running?")
                return
            
            building_options = {b["name"]: b for b in buildings}
            selected_building_name = st.selectbox(
                "🏢 Destination Building",
                list(building_options.keys()),
                key="order_building"
            )
            selected_building = building_options[selected_building_name]
            
            nodes = api.get_delivery_nodes(selected_building["building_id"])
            selected_node = None
            if nodes:
                node_options = {n["node_name"]: n for n in nodes}
                selected_node_name = st.selectbox(
                    "📍 Delivery Node",
                    list(node_options.keys()),
                    key="order_node"
                )
                selected_node = node_options[selected_node_name]
            else:
                st.error("No delivery nodes available")
        
        with col2:
            payload_weight = st.slider(
                "📦 Payload Weight (kg)",
                min_value=0.1, max_value=2.5, value=1.0, step=0.1
            )
            
            payload_desc = st.text_area(
                "Description",
                placeholder="E.g., Medical supplies, food package, documents",
                height=80
            )
        
        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_b:
            if st.button("📤 Place Order", key="place_order_btn"):
                if selected_node and payload_weight > 0:
                    if payload_weight > selected_node["max_payload_kg"]:
                        st.error(f"Payload exceeds node capacity ({selected_node['max_payload_kg']}kg)")
                    else:
                        order = api.place_order(selected_node["node_id"], payload_weight, payload_desc)
                        if order and "order_id" in order:
                            st.success(f"Order placed: {order['order_id']}")
                            
                            # Plan route
                            route = api.plan_route(12.9716, 77.5946, 980.0, selected_node["node_id"])
                            if route and "waypoints" in route:
                                st.info(
                                    f"Route planned — {route['total_distance_m']:.0f} m, "
                                    f"~{route['estimated_duration_s']:.0f} s, risk {route['risk_score']:.2f}"
                                )
                                # Attach route to order
                                api.assign_route_to_order(
                                    order["order_id"],
                                    route["waypoints"],
                                    route["total_distance_m"],
                                    route["estimated_duration_s"],
                                )
                            
                            # Auto-assign best drone
                            assign = api.assign_drone(order["order_id"])
                            if assign and assign.get("drone_id"):
                                st.success(f"Drone assigned: **{assign['drone_id']}**")
                            else:
                                st.warning("No drone available right now — order queued")
                        else:
                            st.error("Failed to place order")
                else:
                    st.warning("Please select a node and enter payload weight")
    
    # Tab 2 - Active Orders
    with tab2:
        st.subheader("Active Orders")
        
        active_statuses = ["placed", "assigned", "in-transit"]
        all_active = []
        for s in active_statuses:
            all_active.extend(api.get_orders(status=s))
        
        if all_active:
            for order in all_active:
                with st.container(border=True):
                    col_info, col_action = st.columns([3, 1])
                    
                    with col_info:
                        st.write(f"**Order ID:** {order['order_id']}")
                        st.write(f"**Destination:** {order['destination_node_id']}")
                        st.write(f"**Payload:** {order['payload_weight_kg']:.1f}kg")
                        st.write(f"**Status:** {order['status']}")
                        if order.get("assigned_drone_id"):
                            st.write(f"**Drone:** {order['assigned_drone_id']}")
                        st.write(f"**Created:** {order['created_at']}")
                        
                        if order.get("estimated_distance_m"):
                            st.metric("Est. Distance", f"{order['estimated_distance_m']:.0f}m")
                    
                    with col_action:
                        if st.button("📊 Track", key=f"track_{order['order_id']}"):
                            st.session_state.tracking_order = order["order_id"]
        else:
            st.info("No active orders")
    
    # Tab 3 - Order History
    with tab3:
        st.subheader("Order History")
        
        orders = api.get_orders()
        
        if orders:
            orders_data = []
            for order in orders:
                orders_data.append({
                    "Order ID": order["order_id"],
                    "Node": order["destination_node_id"],
                    "Payload (kg)": order["payload_weight_kg"],
                    "Status": order["status"],
                    "Drone": order.get("assigned_drone_id") or "—",
                    "Distance (m)": order.get("estimated_distance_m", "—"),
                    "Created": order["created_at"][:10],
                })
            
            df = pd.DataFrame(orders_data)
            st.dataframe(df, use_container_width=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Orders", len(orders))
            with col2:
                st.metric("Delivered", len([o for o in orders if o["status"] == "delivered"]))
            with col3:
                st.metric("Active", len([o for o in orders if o["status"] in active_statuses]))
            with col4:
                st.metric("Failed", len([o for o in orders if o["status"] == "failed"]))
        else:
            st.info("No orders yet")


# ---- Top-level execution for Streamlit multi-page ----
api_url = st.secrets.get("API_URL", "http://localhost:8000")
show(api_url)
