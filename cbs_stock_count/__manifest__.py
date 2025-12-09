# -*- coding: utf-8 -*-
{
    "name": "Stock Count Review",
    "summary": "Physical stock counting with approval workflow and variance tracking.",
    "version": "1.0.0",
    "author": "ByConsult",
    "website": "https://www.cbs.jo/",
    "license": "OPL-1",
    "depends": [
        "stock",
        "mail",
        "account",
    ],
    "data": [

        #data
        "data/sequence.xml",
        # Security
        "security/security.xml",
        "security/ir.model.access.csv",
        # Views
        "views/product_category_views.xml",
        "views/stock_count_line_views.xml",
        "views/stock_count_session_views.xml",
        "wizard/stock_count_wizard_views.xml",
        "views/stock_menus.xml",
        # Reports
        "reports/report_count_sheet.xml",
        "reports/report_final_count.xml",
    ],
}
