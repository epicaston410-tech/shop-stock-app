import datetime
import pandas as pd
import streamlit as st

# ตั้งค่าหน้าตาแอป
st.set_page_config(
    page_title="ระบบสต็อก & สรุปกำไรแบ่งหุ้นส่วน",
    page_icon="🏪",
    layout="wide",
)

st.title("🏪 ระบบจัดการสต็อกสินค้า & สรุปกำไรแบ่งหุ้นส่วน")
st.caption("รองรับสต็อกแยกล็อตต้นทุน + คำนวณกำไรแม่นยำ + ตัดงวดปันผล 50/50")
st.markdown("---")

# ---------------------------------------------------------
# 1. INITIALIZE SESSION STATE (จำลองฐานข้อมูล)
# ---------------------------------------------------------

# 1.1 ตารางสินค้าหลัก
if "products" not in st.session_state:
  st.session_state.products = pd.DataFrame([
      {
          "ProductID": "P001",
          "ProductName": "M-150",
          "Unit": "ขวด",
          "SellingPrice": 12.0,
      },
      {
          "ProductID": "P002",
          "ProductName": "เลย์ รสออริจินัล",
          "Unit": "ซอง",
          "SellingPrice": 20.0,
      },
  ])

# 1.2 ตารางสต็อกแยกล็อต (Stock Lots)
if "stock_lots" not in st.session_state:
  st.session_state.stock_lots = pd.DataFrame([
      {
          "LotID": "LOT-001",
          "ProductID": "P001",
          "BuyDate": "2026-10-15",
          "Supplier": "แม็คโคร",
          "TotalPrice": 450.0,
          "TotalQty": 50,
          "UnitCost": 9.0,  # 450 / 50
          "RemainingQty": 30,
      },
      {
          "LotID": "LOT-002",
          "ProductID": "P001",
          "BuyDate": "2026-10-18",
          "Supplier": "ร้านนอก",
          "TotalPrice": 465.0,
          "TotalQty": 50,
          "UnitCost": 9.3,  # 465 / 50
          "RemainingQty": 50,
      },
  ])

# 1.3 ตารางประวัติการขาย (Sales)
if "sales" not in st.session_state:
  st.session_state.sales = pd.DataFrame(
      columns=[
          "SaleID",
          "Date",
          "ProductID",
          "ProductName",
          "LotID",
          "Qty",
          "UnitCost",
          "SellingPrice",
          "TotalSales",
          "TotalCost",
          "NetProfit",
          "Settled",  # False = งวดปัจจุบัน, True = ปันผลไปแล้ว
      ]
  )

# 1.4 ตารางประวัติการแบ่งกำไร (Settlement History)
if "settlements" not in st.session_state:
  st.session_state.settlements = pd.DataFrame(
      columns=[
          "SettlementID",
          "SettleDate",
          "TotalSales",
          "TotalCost",
          "NetProfit",
          "ProfitPerPartner",
      ]
  )

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

  # ดึงเฉพาะรายการขายในงวดปัจจุบัน (Settled == False)
  current_sales = st.session_state.sales[
      st.session_state.sales["Settled"] == False
  ]

  total_sales = (
      current_sales["TotalSales"].sum() if not current_sales.empty else 0.0
  )
  total_cost = (
      current_sales["TotalCost"].sum() if not current_sales.empty else 0.0
  )
  net_profit = (
      current_sales["NetProfit"].sum() if not current_sales.empty else 0.0
  )
  profit_per_person = net_profit / 2.0

  # สรุปตัวเลขสำคัญ
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

  # ปุ่มกดตัดงวดแบ่งกำไร
  col_btn, col_txt = st.columns([1, 3])
  with col_btn:
    if st.button("🔘 กดสรุป & ตัดรอบแบ่งกำไร", type="primary"):
      if current_sales.empty:
        st.warning("ยังไม่มีรายการขายในงวดนี้ ไม่สามารถตัดรอบได้")
      else:
        # บันทึกประวัติ Settlement
        settle_id = f"SETTL-{len(st.session_state.settlements)+1:03d}"
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        new_settlement = {
            "SettlementID": settle_id,
            "SettleDate": now_str,
            "TotalSales": total_sales,
            "TotalCost": total_cost,
            "NetProfit": net_profit,
            "ProfitPerPartner": profit_per_person,
        }
        st.session_state.settlements = pd.concat(
            [st.session_state.settlements, pd.DataFrame([new_settlement])],
            ignore_index=True,
        )

        # ปรับสถานะรายการขายงวดนี้เป็น Settled = True
        st.session_state.sales.loc[
            st.session_state.sales["Settled"] == False, "Settled"
        ] = True

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
  if not st.session_state.settlements.empty:
    st.dataframe(st.session_state.settlements, use_container_width=True)
  else:
    st.info("ยังไม่มีประวัติการตัดรอบแบ่งกำไร")

# ---------------------------------------------------------
# 4. MENU 2: บันทึกการขายหน้าร้าน
# ---------------------------------------------------------
elif menu == "🛒 บันทึกการขายหน้าร้าน":
  st.subheader("🛒 บันทึกรายการขายสินค้า")

  # รวมสต็อกคงเหลือของสินค้าแต่ละตัว
  products_df = st.session_state.products.copy()
  lots_df = st.session_state.stock_lots.copy()

  # คำนวณสต็อกรวมที่มีอยู่
  stock_summary = (
      lots_df.groupby("ProductID")["RemainingQty"].sum().reset_index()
  )
  products_df = pd.merge(
      products_df, stock_summary, on="ProductID", how="left"
  ).fillna({"RemainingQty": 0})

  with st.form("sale_form"):
    prod_options = {
        row[
            "ProductName"
        ]: f"{row['ProductName']} (คงเหลือ: {int(row['RemainingQty'])} {row['Unit']})"
        for _, row in products_df.iterrows()
    }
    selected_prod_name = st.selectbox(
        "เลือกสินค้า",
        options=list(prod_options.keys()),
        format_func=lambda x: prod_options[x],
    )

    selected_prod = products_df[
        products_df["ProductName"] == selected_prod_name
    ].iloc[0]
    p_id = selected_prod["ProductID"]
    available_qty = int(selected_prod["RemainingQty"])
    unit_name = selected_prod["Unit"]
    sell_price = selected_prod["SellingPrice"]

    sell_qty = st.number_input(
        f"จำนวนที่ขาย ({unit_name})",
        min_value=1,
        max_value=max(1, available_qty),
        value=1,
    )
    custom_price = st.number_input(
        "ราคาขายต่อหน่วย (บาท)", min_value=0.0, value=float(sell_price)
    )

    btn_submit_sale = st.form_submit_button("บันทึกการขาย")

    if btn_submit_sale:
      if available_qty < sell_qty:
        st.error(f"สินค้าคงเหลือไม่พอขาย (มีอยู่ {available_qty} {unit_name})")
      else:
        # ตัดสต็อกแบบ FIFO (ตัดล็อตที่ซื้อมาก่อนก่อน)
        qty_to_sell = sell_qty
        avail_lots = (
            lots_df[
                (lots_df["ProductID"] == p_id) & (lots_df["RemainingQty"] > 0)
            ]
            .sort_values(by="BuyDate")
            .copy()
        )

        for _, lot in avail_lots.iterrows():
          if qty_to_sell <= 0:
            break

          lot_id = lot["LotID"]
          lot_rem = lot["RemainingQty"]
          unit_cost = lot["UnitCost"]

          take_qty = min(qty_to_sell, lot_rem)

          # คำนวณยอด
          tot_sales = take_qty * custom_price
          tot_cost = take_qty * unit_cost
          net_prof = tot_sales - tot_cost

          # ตัดยอดในสต็อกล็อต
          st.session_state.stock_lots.loc[
              st.session_state.stock_lots["LotID"] == lot_id, "RemainingQty"
          ] -= take_qty

          # บันทึกลงตาราง Sales
          sale_id = f"SALE-{len(st.session_state.sales)+1:04d}"
          now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

          new_sale = {
              "SaleID": sale_id,
              "Date": now_str,
              "ProductID": p_id,
              "ProductName": selected_prod_name,
              "LotID": lot_id,
              "Qty": take_qty,
              "UnitCost": unit_cost,
              "SellingPrice": custom_price,
              "TotalSales": tot_sales,
              "TotalCost": tot_cost,
              "NetProfit": net_prof,
              "Settled": False,
          }
          st.session_state.sales = pd.concat(
              [st.session_state.sales, pd.DataFrame([new_sale])],
              ignore_index=True,
          )

          qty_to_sell -= take_qty

        st.success(
            f"บันทึกขาย {selected_prod_name} จำนวน {sell_qty} {unit_name} เรียบร้อย!"
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
    with st.form("add_lot_form"):
      prod_list = st.session_state.products["ProductName"].tolist()
      p_name = st.selectbox("เลือกสินค้า", prod_list)

      col_a, col_b = st.columns(2)
      buy_date = col_a.date_input("วันที่ซื้อ/รับเข้า", datetime.date.today())
      supplier = col_b.text_input("แหล่งที่ซื้อ (เช่น แม็คโคร, ร้านนอก)", "แม็คโคร")

      col_c, col_d = st.columns(2)
      tot_price = col_c.number_input(
          "ราคารวมที่ซื้อมาทั้งหมด (บาท)", min_value=0.0, value=450.0
      )
      tot_qty = col_d.number_input(
          "จำนวนทั้งหมดที่ได้ (ขวด/ซอง/ห่อ/ชิ้น)", min_value=1, value=50
      )

      # คำนวณต้นทุนต่อหน่วยแบบ Real-time
      calculated_unit_cost = tot_price / tot_qty if tot_qty > 0 else 0.0
      st.info(
          f"💡 ต้นทุนต่อหน่วยอัตโนมัติ = **฿{calculated_unit_cost:,.2f}** บาท/หน่วย"
      )

      btn_add_lot = st.form_submit_button("บันทึกเข้าสต็อก")

      if btn_add_lot:
        p_id = st.session_state.products[
            st.session_state.products["ProductName"] == p_name
        ].iloc[0]["ProductID"]
        lot_id = f"LOT-{len(st.session_state.stock_lots)+1:03d}"

        new_lot = {
            "LotID": lot_id,
            "ProductID": p_id,
            "BuyDate": str(buy_date),
            "Supplier": supplier,
            "TotalPrice": tot_price,
            "TotalQty": tot_qty,
            "UnitCost": calculated_unit_cost,
            "RemainingQty": tot_qty,
        }
        st.session_state.stock_lots = pd.concat(
            [st.session_state.stock_lots, pd.DataFrame([new_lot])],
            ignore_index=True,
        )
        st.success(
            f"เพิ่มสต็อก {p_name} จำนวน {tot_qty} หน่วย (ทุน ฿{calculated_unit_cost:,.2f}/หน่วย) สำเร็จ!"
        )
        st.rerun()

  with tab_new_product:
    with st.form("add_product_form"):
      new_p_name = st.text_input("ชื่อสินค้าใหม่")
      new_unit = st.selectbox(
          "หน่วยนับ", ["ขวด", "ซอง", "ห่อ", "ชิ้น", "กล่อง", "กระป๋อง"]
      )
      default_sell_price = st.number_input(
          "ราคาขายตั้งต้นหน้าร้าน (บาท)", min_value=0.0, value=15.0
      )

      btn_add_prod = st.form_submit_button("เพิ่มรายการสินค้า")

      if btn_add_prod and new_p_name:
        new_p_id = f"P{len(st.session_state.products)+1:03d}"
        new_prod = {
            "ProductID": new_p_id,
            "ProductName": new_p_name,
            "Unit": new_unit,
            "SellingPrice": default_sell_price,
        }
        st.session_state.products = pd.concat(
            [st.session_state.products, pd.DataFrame([new_prod])],
            ignore_index=True,
        )
        st.success(f"เพิ่มสินค้าใหม่ '{new_p_name}' เรียบร้อยแล้ว")
        st.rerun()

# ---------------------------------------------------------
# 6. MENU 4: ดูสต็อกสินค้าคงเหลือ
# ---------------------------------------------------------
elif menu == "📦 ดูสต็อกสินค้าคงเหลือ":
  st.subheader("📦 รายการสต็อกสินค้าแยกตามล็อตซื้อเข้า")

  # ตารางแสดงสต็อกตามล็อต
  lots_df = st.session_state.stock_lots.copy()
  prods_df = st.session_state.products.copy()

  merged_lots = pd.merge(lots_df, prods_df, on="ProductID", how="left")
  display_lots = merged_lots[[
      "LotID",
      "ProductName",
      "Supplier",
      "BuyDate",
      "TotalPrice",
      "TotalQty",
      "UnitCost",
      "RemainingQty",
      "Unit",
  ]]

  st.dataframe(display_lots, use_container_width=True)
