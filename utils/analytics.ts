import { ImwebOrder, ImwebOrderItem } from '../types';
import * as XLSX from 'xlsx';

// --- SALES ANALYTICS ---

export const calculateKPIs = (orders: ImwebOrder[]) => {
  const totalRevenue = orders.reduce((sum, order) => sum + order.pay_price, 0);
  const totalOrders = orders.length;
  const averageOrderValue = totalOrders > 0 ? totalRevenue / totalOrders : 0;
  const totalItemsSold = orders.reduce((sum, order) => {
    return sum + order.items.reduce((iSum, item) => iSum + item.amount, 0);
  }, 0);

  return { totalRevenue, totalOrders, averageOrderValue, totalItemsSold };
};

export const getDailyRevenue = (orders: ImwebOrder[]) => {
  const dailyMap = new Map<string, number>();

  orders.forEach(order => {
    const date = new Date(order.payment_date * 1000).toISOString().split('T')[0];
    dailyMap.set(date, (dailyMap.get(date) || 0) + order.pay_price);
  });

  return Array.from(dailyMap.entries())
    .map(([date, amount]) => ({ date, amount }))
    .sort((a, b) => a.date.localeCompare(b.date));
};

export const getProductRevenue = (orders: ImwebOrder[]) => {
  const prodMap = new Map<string, number>();

  orders.forEach(order => {
    order.items.forEach(item => {
      prodMap.set(item.product_name, (prodMap.get(item.product_name) || 0) + (item.price * item.amount));
    });
  });

  return Array.from(prodMap.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
};

// --- INVOICE GENERATOR LOGIC ---

// Helper for natural sort of strings containing numbers (e.g., "Option 2" before "Option 10")
const naturalSort = (a: string, b: string) => {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
};

export const generateInvoiceData = (orders: ImwebOrder[]) => {
  return orders.map(order => {
    // Logic: Repeat option name N times based on amount, join with " // "
    const processedItems: string[] = [];
    
    order.items.forEach(item => {
      const name = `${item.product_name} [${item.option_name}]`;
      for (let i = 0; i < item.amount; i++) {
        processedItems.push(name);
      }
    });

    // Sort items naturally
    processedItems.sort(naturalSort);

    const formattedItems = processedItems.join(' // ');

    return {
      '주문번호': order.order_no,
      '수령인': order.shipping_address.name,
      '전화번호': order.shipping_address.tel,
      '우편번호': order.shipping_address.postcode,
      '주소': order.shipping_address.address,
      '상세주소': order.shipping_address.address_detail,
      '상품명(변환됨)': formattedItems,
      '배송메모': '구매해 주셔서 감사합니다!', // Static or from order memo if available
      '결제금액': order.pay_price,
      '주문상태': order.order_status,
      '주문일자': new Date(order.payment_date * 1000).toLocaleDateString(),
    };
  });
};

export const downloadExcel = (data: any[], filename: string) => {
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Invoices");
  XLSX.writeFile(wb, `${filename}.xlsx`);
};

// --- INVENTORY ---

export const getTopOptions = (orders: ImwebOrder[]) => {
  const optionMap = new Map<string, number>();

  orders.forEach(order => {
    order.items.forEach(item => {
      const key = `${item.product_name} - ${item.option_name}`;
      optionMap.set(key, (optionMap.get(key) || 0) + item.amount);
    });
  });

  return Array.from(optionMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
};

// --- CUSTOMER ---

export const getVipCustomers = (orders: ImwebOrder[]) => {
  const customerMap = new Map<string, { name: string, count: number, totalSpent: number, city: string }>();

  orders.forEach(order => {
    const email = order.billing_person.email || order.order_no; // Fallback ID
    const current = customerMap.get(email) || { 
      name: order.billing_person.name, 
      count: 0, 
      totalSpent: 0,
      city: order.shipping_address.address.split(' ')[0] // Simple city extraction
    };

    customerMap.set(email, {
      ...current,
      count: current.count + 1,
      totalSpent: current.totalSpent + order.pay_price
    });
  });

  return Array.from(customerMap.values())
    .sort((a, b) => b.totalSpent - a.totalSpent)
    .slice(0, 20); // Top 20 VIPs
};

export const getCityStats = (orders: ImwebOrder[]) => {
  const cityMap = new Map<string, number>();
  orders.forEach(order => {
    const city = order.shipping_address.address.split(' ')[0] || 'Unknown';
    cityMap.set(city, (cityMap.get(city) || 0) + 1);
  });
  
  return Array.from(cityMap.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
};