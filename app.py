import datetime
import pandas as pd
import streamlit as st
from supabase import create_client

# ตั้งค่าหน้าตาแอป
st.set_page_config(
    page_title="ระบบสต็อก & สรุปกำไรแบ่งหุ้นส่วน",
    page_icon="🏪",
    layout="wide",
)


# ---------------------------------------------------------
# 1. CONNECT TO SUPABASE
# ---------------------------------------------------------
@st.cache_resource
def init_supabase():
  url = st.secrets["SUPABASE_URL"]
  key = st.secrets["SUPABASE_KEY"]
  return create_client(url, key)


supabase = init_supabase()

st.title("🏪 ระบบจัดการสต็อกสินค้า & สรุปกำไรแบ่งหุ้นส่วน")
st.caption(
    "เชื่อมต่อฐานข้อมูลถาวร Supabase + ตัดสต็อก FIFO + ตัดงวดปันผล 50/50"
)
st.markdown("---")

# ---------------------------------------------------------
# 2. SIDEBAR MENU
# ---------------------------------------------------------
menu = st.sidebar.selectbox(
    "📌 เลือกเมนูการทำงาน",
    [
        "💰 สรุปงวดกำไร & แบ่งปันผล",
        "🛒 บันทึกการขายหน้าร้าน",
        "📥 บันทึกรับสินค้าเข้าสต็อก (แยกล็อต)",
        "📦 ดูสต็อกสินค้าคงเหลือ",
    ],
)

# ---------------------------------------------------------
# 3. MENU 1: สรุปงวดกำไร & แบ่งปันผล
# ---------------------------------------------------------
if menu == "💰 สรุปงวดกำไร & แบ่งปันผล":
  st.subheader("💰 สรุปผลประกอบการงวดปัจจุบัน (ยังไม่ได้ตัดรอบแบ่งกำไร)")

  # ดึงข้อมูลการขายที่ยังไม่ได้ตัดรอบ (settled = False)
  response = (
      supabase.table("sales").select("*").eq("settled", False).execute()
  )
  sales_data = response.data
  current_sales = pd.DataFrame(sales_data) if sales_data else pd.DataFrame()

  total_sales = (
      float(current_sales["total_sales"].sum())
      if not current_sales.empty
      else 0.0
  )
  total_cost = (
      float(current_sales["total_cost"].sum())
      if not current_sales.empty
      else 0.0
  )
  net_profit = (
      float(current_sales["net_profit"].sum())
      if not current_sales.empty
      else 0.0
  )
  profit_per_person = net_profit / 2.0

  # แสดงตัวเลขสรุป
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("ยอดขายรวมงวดนี้", f"฿{total_sales:,.2f}")
  c2.metric("ต้นทุนรวมงวดนี้", f"฿{total_cost:,.2f}")
  c3.metric("กำไรสุทธิรวม", f"฿{net_profit:,.2f}")
  c4.metric(
      "แบ่งปันผล (คนละ 50%)",
      f"฿{profit_per_person:,.2f}",
      delta_color="normal",
  )

  st.markdown("---")

  col_btn, col_txt = st.columns([1, 3])
  with col_btn:
    if st.button("🔘 กดสรุป & ตัดรอบแบ่งกำไร", type="primary"):
      if current_sales.empty:
        st.warning("ยังไม่มีรายการขายในงวดนี้ ไม่สามารถตัดรอบได้")
      else:
        # 1. บันทึกประวัติการตัดรอบลงตาราง settlements
        settle_id = f"SETTL-{int(datetime.datetime.now().timestamp())}"
        now_str = datetime.datetime.now().isoformat()

        supabase.table("settlements").insert({
            "settlement_id": settle_id,
            "settle_date": now_str,
            "total_sales": total_sales,
            "total_cost": total_cost,
            "net_profit": net_profit,
            "profit_per_partner": profit_per_person,
        }).execute()

        # 2. ปรับสถานะรายการขายทั้งหมดในงวดนี้เป็น settled = True
        supabase.table("sales").update({"settled": True}).eq(
            "settled", False
        ).execute()

        st.balloons()
        st.success(
            f"ตัดรอบสำเร็จ! บันทึกยอดปันผลแบ่งคนละ ฿{profit_per_person:,.2f} เรียบร้อยแล้ว สต็อกสินค้าคงเหลือเท่าเดิม และเริ่มนับงวดใหม่ทันที"
        )
        st.rerun()

  with col_txt:
    st.caption(
        "⚡ หมายเหตุ: การกดปุ่มนี้จะไม่ทำให้จำนวนสต็อกสินค้าลดลง"
        " แต่จะทำการรีเซ็ตยอดกำไรสะสมเพื่อเริ่มนับ 1 ใหม่ในงวดถัดไป"
    )

  st.markdown("---")
  st.subheader("📋 รายการขายในงวดปัจจุบัน")
  if not current_sales.empty:
    st.dataframe(current_sales, use_container_width=True)
  else:
    st.info("ยังไม่มีรายการขายในงวดปัจจุบัน")

  st.markdown("---")
  st.subheader("📜 ประวัติการตัดรอบแบ่งกำไรย้อนหลัง")
  settle_res = (
      supabase.table("settlements")
      .select("*")
      .order("settle_date", desc=True)
      .execute()
  )
  if settle_res.data:
    st.dataframe(pd.DataFrame(settle_res.data), use_container_width=True)
  else:
    st.info("ยังไม่มีประวัติการตัดรอบแบ่งกำไร")

# ---------------------------------------------------------
# 4. MENU 2: บันทึกการขายหน้าร้าน (อัปเดตรองรับตัดสต็อกแก้ว)
# ---------------------------------------------------------
elif menu == "🛒 บันทึกการขายหน้าร้าน":
  st.subheader("🛒 บันทึกรายการขายสินค้า")

  prods = supabase.table("products").select("*").execute().data
  lots = (
      supabase.table("stock_lots")
      .select("*")
      .gt("remaining_qty", 0)
      .order("buy_date")
      .execute()
      .data
  )

  if not prods:
    st.warning("กรุณาเพิ่มรายการสินค้าในระบบก่อน")
  else:
    prods_df = pd.DataFrame(prods)
    lots_df = pd.DataFrame(lots) if lots else pd.DataFrame()

    if not lots_df.empty:
      stock_summary = (
          lots_df.groupby("product_id")["remaining_qty"].sum().reset_index()
      )
      prods_df = pd.merge(
          prods_df, stock_summary, on="product_id", how="left"
      ).fillna({"remaining_qty": 0})
    else:
      prods_df["remaining_qty"] = 0

    # ตรวจสอบหาว่ามีสินค้าชื่อ 'แก้วกระดาษ' ในระบบไหม
    cup_prod = prods_df[
        prods_df["product_name"].str.contains("แก้วกระดาษ|แก้ว", na=False)
    ]
    cup_available = not cup_prod.empty

    with st.form("sale_form"):
      prod_options = {
          row[
              "product_name"
          ]: f"{row['product_name']} (คงเหลือ: {int(row['remaining_qty'])} {row['unit']})"
          for _, row in prods_df.iterrows()
      }
      selected_prod_name = st.selectbox(
          "เลือกสินค้าหลัก",
          options=list(prod_options.keys()),
          format_func=lambda x: prod_options[x],
      )

      selected_prod = prods_df[
          prods_df["product_name"] == selected_prod_name
      ].iloc[0]
      p_id = selected_prod["product_id"]
      available_qty = int(selected_prod["remaining_qty"])
      unit_name = selected_prod["unit"]
      sell_price = float(selected_prod["selling_price"])

      col1, col2 = st.columns(2)
      sell_qty = col1.number_input(
          f"จำนวนที่ขาย ({unit_name})",
          min_value=1,
          max_value=max(1, available_qty),
          value=1,
      )
      custom_price = col2.number_input(
          "ราคาขายต่อหน่วย (บาท)", min_value=0.0, value=sell_price
      )

      # Option เพิ่มเติม: แถมแก้วกระดาษไหม?
      include_cup = False
      if cup_available:
        cup_row = cup_prod.iloc[0]
        cup_rem = int(cup_row["remaining_qty"])
        include_cup = st.checkbox(
            f"🥤 รับ 'แก้วกระดาษ' ด้วย (+{sell_qty} ใบ) [สต็อกคงเหลือ: {cup_rem} ใบ]"
        )

      btn_submit_sale = st.form_submit_button("💾 บันทึกการขาย", type="primary")

      if btn_submit_sale:
        if available_qty < sell_qty:
          st.error(f"สินค้าคงเหลือไม่พอขาย (มีอยู่ {available_qty} {unit_name})")
        else:
          # ฟังก์ชันตัดสต็อก FIFO แยกรายสินค้า
          def deduct_stock_fifo(prod_id, qty_needed):
            avail_lots = [lot for lot in lots if lot["product_id"] == prod_id]
            used_lots_cost = 0.0
            remaining_to_deduct = qty_needed

            for lot in avail_lots:
              if remaining_to_deduct <= 0:
                break
              lot_id = lot["lot_id"]
              lot_rem = int(lot["remaining_qty"])
              unit_cost = float(lot["unit_cost"])

              take_qty = min(remaining_to_deduct, lot_rem)
              used_lots_cost += take_qty * unit_cost

              # อัปเดตใน stock_lots
              supabase.table("stock_lots").update(
                  {"remaining_qty": lot_rem - take_qty}
              ).eq("lot_id", lot_id).execute()
              remaining_to_deduct -= take_qty

            return used_lots_cost

          # 1. ตัดสต็อกสินค้าหลัก
          main_cost = deduct_stock_fifo(p_id, sell_qty)

          # 2. ถ้ามีตัดสต็อกแก้วกระดาษเพิ่ม
          cup_cost = 0.0
          if include_cup and cup_available:
            cup_p_id = cup_prod.iloc[0]["product_id"]
            cup_cost = deduct_stock_fifo(cup_p_id, sell_qty)

          # 3. บันทึกลงตาราง sales
          tot_sales = sell_qty * custom_price
          tot_cost = main_cost + cup_cost
          net_prof = tot_sales - tot_cost

          sale_id = f"SALE-{int(datetime.datetime.now().timestamp())}"
          sale_item_name = (
              f"{selected_prod_name} (+แก้ว)"
              if include_cup
              else selected_prod_name
          )

          supabase.table("sales").insert({
              "sale_id": sale_id,
              "product_id": p_id,
              "product_name": sale_item_name,
              "qty": sell_qty,
              "unit_cost": tot_cost / sell_qty if sell_qty > 0 else 0,
              "selling_price": custom_price,
              "total_sales": tot_sales,
              "total_cost": tot_cost,
              "net_profit": net_prof,
              "settled": False,
          }).execute()

          st.success(
              f"บันทึกขาย {sale_item_name} จำนวน {sell_qty} {unit_name} เรียบร้อย!"
          )
          st.rerun()

# ---------------------------------------------------------
# 5. MENU 3: บันทึกรับสินค้าเข้าสต็อก (แยกล็อต)
# ---------------------------------------------------------
elif menu == "📥 บันทึกรับสินค้าเข้าสต็อก (แยกล็อต)":
  st.subheader("📥 บันทึกรับสินค้าเข้าสต็อก (ซื้อของมาเติม)")

  tab_new_lot, tab_new_product = st.tabs(
      ["ซื้อของเข้าสต็อก (ล็อตใหม่)", "เพิ่มรายชื่อสินค้าใหม่"]
  )

  with tab_new_lot:
    prods = supabase.table("products").select("*").execute().data
    if not prods:
      st.warning("กรุณาเพิ่มสินค้าใหม่ในแท็บ 'เพิ่มรายชื่อสินค้าใหม่' ก่อนครับ")
    else:
      with st.form("add_lot_form"):
        prod_names = [p["product_name"] for p in prods]
        p_name = st.selectbox("เลือกสินค้า", prod_names)

        col_a, col_b = st.columns(2)
        buy_date = col_a.date_input("วันที่ซื้อ/รับเข้า", datetime.date.today())
        supplier = col_b.text_input(
            "แหล่งที่ซื้อ (เช่น แม็คโคร, ร้านนอก)", "แม็คโคร"
        )

        col_c, col_d = st.columns(2)
        tot_price = col_c.number_input(
            "ราคารวมที่ซื้อมาทั้งหมด (บาท)", min_value=0.0, value=450.0
        )
        tot_qty = col_d.number_input(
            "จำนวนทั้งหมดที่ได้ (ขวด/ซอง/ห่อ/ชิ้น/ใบ)", min_value=1, value=50
        )

        calculated_unit_cost = tot_price / tot_qty if tot_qty > 0 else 0.0
        st.info(
            f"💡 ต้นทุนต่อหน่วยอัตโนมัติ = **฿{calculated_unit_cost:,.2f}** บาท/หน่วย"
        )

        btn_add_lot = st.form_submit_button("บันทึกเข้าสต็อก")

        if btn_add_lot:
          p_id = [p["product_id"] for p in prods if p["product_name"] == p_name][
              0
          ]
          lot_id = f"LOT-{int(datetime.datetime.now().timestamp())}"

          supabase.table("stock_lots").insert({
              "lot_id": lot_id,
              "product_id": p_id,
              "buy_date": str(buy_date),
              "supplier": supplier,
              "total_price": tot_price,
              "total_qty": tot_qty,
              "unit_cost": calculated_unit_cost,
              "remaining_qty": tot_qty,
          }).execute()

          st.success(
              f"เพิ่มสต็อก {p_name} จำนวน {tot_qty} หน่วย (ทุน ฿{calculated_unit_cost:,.2f}/หน่วย) สำเร็จ!"
          )
          st.rerun()

  with tab_new_product:
    with st.form("add_product_form"):
      new_p_name = st.text_input("ชื่อสินค้าใหม่")
      new_unit = st.selectbox(
          "หน่วยนับ", ["ขวด", "ซอง", "ห่อ", "ชิ้น", "กล่อง", "กระป๋อง", "ใบ"]
      )
      default_sell_price = st.number_input(
          "ราคาขายตั้งต้นหน้าร้าน (บาท)", min_value=0.0, value=15.0
      )

      btn_add_prod = st.form_submit_button("เพิ่มรายการสินค้า")

      if btn_add_prod and new_p_name:
        new_p_id = f"P-{int(datetime.datetime.now().timestamp())}"
        supabase.table("products").insert({
            "product_id": new_p_id,
            "product_name": new_p_name,
            "unit": new_unit,
            "selling_price": default_sell_price,
        }).execute()

        st.success(f"เพิ่มสินค้าใหม่ '{new_p_name}' เรียบร้อยแล้ว")
        st.rerun()

# ---------------------------------------------------------
# 6. MENU 4: ดูสต็อกสินค้าคงเหลือ
# ---------------------------------------------------------
elif menu == "📦 ดูสต็อกสินค้าคงเหลือ":
  st.subheader("📦 รายการสต็อกสินค้าแยกตามล็อตซื้อเข้า")

  lots_res = supabase.table("stock_lots").select("*").execute()
  prods_res = supabase.table("products").select("*").execute()

  if lots_res.data and prods_res.data:
    lots_df = pd.DataFrame(lots_res.data)
    prods_df = pd.DataFrame(prods_res.data)

    merged = pd.merge(lots_df, prods_df, on="product_id", how="left")
    st.dataframe(merged, use_container_width=True)
  else:
    st.info("ยังไม่มีข้อมูลสต็อกสินค้า")
