export interface ImwebOrder {
  order_no: string;
  order_status: string;
  payment_date: number; // Unix timestamp
  pay_price: number;
  total_price: number;
  items: ImwebOrderItem[];
  billing_person: {
    name: string;
    email: string;
    tel: string;
    address: string;
  };
  shipping_address: {
    name: string;
    tel: string;
    address: string;
    address_detail: string;
    postcode: string;
  };
}

export interface ImwebOrderItem {
  item_no: string;
  product_name: string;
  option_name: string;
  amount: number; // Quantity
  price: number;
  status: string;
}

export interface DashboardState {
  orders: ImwebOrder[];
  apiKey: string;
  apiSecret: string;
  startDate: string;
  endDate: string;
  isLoading: boolean;
  error: string | null;
  lastSyncTime: Date | null;
}

export enum TabType {
  SALES = 'SALES',
  INVOICE = 'INVOICE',
  GROUP_BUY = 'GROUP_BUY',
  INVENTORY = 'INVENTORY',
  CUSTOMER = 'CUSTOMER',
  DATA_SYNC = 'DATA_SYNC'
}