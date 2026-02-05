import { ImwebOrder } from '../types';

// Helper to simulate API delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Mock Data Generator for Demo Mode
export const generateMockOrders = (count: number): ImwebOrder[] => {
  const orders: ImwebOrder[] = [];
  const products = [
    { name: '수분 진정 크림', price: 25000, options: ['50ml', '100ml (2개입)'] },
    { name: '비타민 C 세럼', price: 42000, options: ['기본 패키지'] },
    { name: '데일리 선블록 SPF50', price: 18000, options: ['튜브형', '스틱형'] },
    { name: '시카 마스크팩', price: 30000, options: ['10매입', '20매입 대용량'] },
  ];

  const cities = ['서울', '부산', '인천', '대구', '대전', '광주', '경기', '강원'];
  const firstNames = ['민준', '서준', '도윤', '예준', '시우', '하준', '지호', '지유', '서윤', '서연'];
  const lastNames = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임'];

  for (let i = 0; i < count; i++) {
    const prod = products[Math.floor(Math.random() * products.length)];
    const city = cities[Math.floor(Math.random() * cities.length)];
    const quantity = Math.floor(Math.random() * 3) + 1;
    const name = lastNames[Math.floor(Math.random() * lastNames.length)] + firstNames[Math.floor(Math.random() * firstNames.length)];
    
    // Random date within last 30 days
    const date = new Date();
    date.setDate(date.getDate() - Math.floor(Math.random() * 30));
    
    orders.push({
      order_no: `ORD-${20230000 + i}`,
      order_status: 'PAYMENT_COMPLETED',
      payment_date: Math.floor(date.getTime() / 1000),
      pay_price: prod.price * quantity,
      total_price: prod.price * quantity,
      items: [
        {
          item_no: `ITM-${i}`,
          product_name: prod.name,
          option_name: prod.options[Math.floor(Math.random() * prod.options.length)],
          amount: quantity,
          price: prod.price,
          status: 'PAYMENT_COMPLETED'
        }
      ],
      billing_person: {
        name: name,
        email: `cust${i}@example.com`,
        tel: '010-1234-5678',
        address: `${city}시 강남구`
      },
      shipping_address: {
        name: name,
        tel: '010-9876-5432',
        address: `${city}시 XX구 YY동`,
        address_detail: '101동 101호',
        postcode: '12345'
      }
    });
  }
  return orders;
};

// Real API Fetch Logic
export const fetchImwebOrders = async (key: string, secret: string, start: string, end: string): Promise<ImwebOrder[]> => {
  // NOTE: In a real browser environment, calling Imweb API directly might trigger CORS.
  // This code assumes a proxy is set up or the API supports CORS.
  // For this demo, we will check if the key is "DEMO" and return mock data.
  
  if (key === 'DEMO') {
    await delay(1500);
    return generateMockOrders(150);
  }

  try {
    // 1. Get Token
    const authRes = await fetch('https://api.imweb.me/v2/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, secret })
    });
    
    if (!authRes.ok) throw new Error('인증에 실패했습니다. API 키를 확인해주세요.');
    const authData = await authRes.json();
    const token = authData.access_token;

    // 2. Get Orders (Simplified: fetching 1st page or up to limit)
    // Note: Imweb API requires timestamps in Unix format or specific string format depending on version.
    // We'll use the timestamp conversion for simplicity.
    const startTime = Math.floor(new Date(start).getTime() / 1000);
    const endTime = Math.floor(new Date(end).getTime() / 1000);

    const ordersRes = await fetch(`https://api.imweb.me/v2/shop/orders?payment_date_from=${startTime}&payment_date_to=${endTime}&limit=100`, {
      method: 'GET',
      headers: { 'access-token': token }
    });

    if (!ordersRes.ok) throw new Error('주문 정보를 불러오는데 실패했습니다.');
    const ordersData = await ordersRes.json();
    
    return ordersData.data.list as ImwebOrder[];
  } catch (error: any) {
    console.error("API Error:", error);
    throw new Error(error.message || '알 수 없는 API 오류가 발생했습니다.');
  }
};