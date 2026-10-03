st.markdown("---")
st.markdown("### 📊 Technical Challenge Predictions")

if cur_w >= 8:
    num_b = len(active_for_week)
    st.write(f"Rank all {num_b} Bakers for the Technical Challenge:")
    tech_ranks = []
    for i in range(num_b):
        rank_str = "1st" if i==0 else ("2nd" if i==1 else ("3rd" if i==2 else f"{i+1}th"))
        saved_t = saved_weekly.get("tech_rank", [])
        t_def = saved_t[i] if (isinstance(saved_t, list) and i < len(saved_t)) else active_for_week[i % len(active_for_week)]
        t_idx = active_for_week.index(t_def) if t_def in active_for_week else 0
        sel_b = st.selectbox(f"Predicted Technical {rank_str} Place:", active_for_week, index=t_idx, key=f"user_tech_r{i}_w{cur_w}")
        tech_ranks.append(sel_b)
    w_picks["tech_rank"] = tech_ranks
else:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("**Top 3 Technical:**")
        saved_top = saved_weekly.get("tech_top_3", [])
        t1_def = saved_top[0] if len(saved_top) > 0 and saved_top[0] in active_for_week else active_for_week[0]
        t2_def = saved_top[1] if len(saved_top) > 1 and saved_top[1] in active_for_week else active_for_week[0]
        t3_def = saved_top[2] if len(saved_top) > 2 and saved_top[2] in active_for_week else active_for_week[0]
        
        tp1 = st.selectbox("1st Place:", active_for_week, index=active_for_week.index(t1_def) if t1_def in active_for_week else 0, key=f"p_t1_w{cur_w}")
        tp2 = st.selectbox("2nd Place:", active_for_week, index=active_for_week.index(t2_def) if t2_def in active_for_week else 0, key=f"p_t2_w{cur_w}")
        tp3 = st.selectbox("3rd Place:", active_for_week, index=active_for_week.index(t3_def) if t3_def in active_for_week else 0, key=f"p_t3_w{cur_w}")
        w_picks["tech_top_3"] = [tp1, tp2, tp3]
        
    with col_t2:
        st.markdown("**Bottom 3 Technical:**")
        saved_bot = saved_weekly.get("tech_bottom_3", [])
        b1_def = saved_bot[0] if len(saved_bot) > 0 and saved_bot[0] in active_for_week else active_for_week[0]
        b2_def = saved_bot[1] if len(saved_bot) > 1 and saved_bot[1] in active_for_week else active_for_week[0]
        b3_def = saved_bot[2] if len(saved_bot) > 2 and saved_bot[2] in active_for_week else active_for_week[0]
        
        bp1 = st.selectbox("3rd-to-Last Place:", active_for_week, index=active_for_week.index(b1_def) if b1_def in active_for_week else 0, key=f"p_b1_w{cur_w}")
        bp2 = st.selectbox("2nd-to-Last Place:", active_for_week, index=active_for_week.index(b2_def) if b2_def in active_for_week else 0, key=f"p_b2_w{cur_w}")
        bp3 = st.selectbox("Last Place:", active_for_week, index=active_for_week.index(b3_def) if b3_def in active_for_week else 0, key=f"p_b3_w{cur_w}")
        w_picks["tech_bottom_3"] = [bp1, bp2, bp3]
