const mockData = [
    {
        id: 1,
        name: "은행동 탑클래스 영어학원",
        category: "영어",
        address: "경기도 시흥시 은행로 123, 2층",
        phone: "031-123-4567",
        rating: 4.8,
        reviewCount: 42,
        image: "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&w=600&q=80",
        description: "초등학생을 위한 몰입형 영어 프로그램. 파닉스부터 스토리텔링까지 완벽 대비.",
        programs: [
            { name: "여름방학 몰입 파닉스 캠프", duration: "4주", time: "오전 10:00 - 12:00", price: "250,000원" },
            { name: "원어민 스토리텔링 특강", duration: "8주", time: "오후 2:00 - 3:30", price: "300,000원" }
        ],
        reviews: [
            { author: "은우맘", date: "2026.05.12", content: "아이가 영어를 너무 싫어했는데 원어민 선생님 특강 듣고 흥미를 붙였어요!", rating: 5 },
            { author: "시흥주민", date: "2026.04.20", content: "시설이 깔끔하고 선생님들이 친절합니다. 셔틀버스 운행해서 좋아요.", rating: 4 }
        ],
        mapUrl: "https://map.kakao.com/?q=경기도+시흥시+은행로+123"
    },
    {
        id: 2,
        name: "마린보이 수영교실",
        category: "수영",
        address: "경기도 시흥시 대은로 45, 지하 1층",
        phone: "031-234-5678",
        rating: 4.9,
        reviewCount: 128,
        image: "https://images.unsplash.com/photo-1519315901367-f34ff9154487?auto=format&fit=crop&w=600&q=80",
        description: "안전하고 깨끗한 해수풀! 소수 정예(1:4) 레슨으로 물에 대한 두려움을 극복합니다.",
        programs: [
            { name: "방학특강 생존수영", duration: "2주", time: "오후 1:00 - 1:50", price: "180,000원" },
            { name: "초등 속성 자유형/배영 마스터", duration: "4주", time: "오후 3:00 - 3:50", price: "200,000원" }
        ],
        reviews: [
            { author: "수영짱", date: "2026.06.01", content: "물 무서워하던 아이가 이제 잠수도 합니다. 선생님 열정이 대단하심.", rating: 5 },
            { author: "행복한가족", date: "2026.03.15", content: "물이 따뜻해서 감기 걱정 안해도 돼서 너무 좋았어요.", rating: 5 }
        ],
        mapUrl: "https://map.kakao.com/?q=경기도+시흥시+대은로+45"
    },
    {
        id: 3,
        name: "FC 골든보이 축구아카데미",
        category: "축구",
        address: "경기도 시흥시 은행동 산 12-3 (실내/외 구장)",
        phone: "031-345-6789",
        rating: 4.7,
        reviewCount: 85,
        image: "https://images.unsplash.com/photo-1518605368461-1ee7c683ee86?auto=format&fit=crop&w=600&q=80",
        description: "프로 출신 코치진의 체계적인 훈련! 즐겁게 뛰며 체력과 협동심을 기릅니다.",
        programs: [
            { name: "주말 기초반 (초 1-3)", duration: "상시", time: "토/일 오전 10:00", price: "120,000원(월)" },
            { name: "여름방학 체력증진 매일반", duration: "4주", time: "월-금 오후 4:00", price: "250,000원" }
        ],
        reviews: [
            { author: "동건대디", date: "2026.05.28", content: "에너지 넘치는 아들 힘 빼놓기 최고입니다. 밥도 잘먹고 일찍 자요ㅋㅋ", rating: 5 },
            { author: "축구팬", date: "2026.05.02", content: "실내 구장이 있어서 비오는 날에도 훈련해서 좋습니다.", rating: 4 }
        ],
        mapUrl: "https://map.kakao.com/?q=경기도+시흥시+은행동"
    },
    {
        id: 4,
        name: "코드플라이 코딩학원",
        category: "코딩",
        address: "경기도 시흥시 은계중앙로 78, 4층",
        phone: "031-456-7890",
        rating: 4.6,
        reviewCount: 34,
        image: "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=600&q=80",
        description: "엔트리, 스크래치부터 파이썬까지. 창의적인 사고력을 길러주는 SW 교육.",
        programs: [
            { name: "여름방학 로봇 코딩 캠프", duration: "2주", time: "오전 10:30 - 12:30", price: "350,000원(교구포함)" },
            { name: "게임 만들기 기초 (스크래치)", duration: "4주", time: "오후 2:30 - 4:00", price: "180,000원" }
        ],
        reviews: [
            { author: "지민어머님", date: "2026.04.10", content: "아이가 자기가 만든 게임이라고 보여주는데 엄청 뿌듯해하네요.", rating: 5 },
            { author: "테크맘", date: "2026.02.20", content: "강사님이 1:1로 잘 봐주시는 편입니다. 진도가 약간 빠른듯해요.", rating: 4 }
        ],
        mapUrl: "https://map.kakao.com/?q=경기도+시흥시+은계중앙로+78"
    },
    {
        id: 5,
        name: "은행 영재 수학학원",
        category: "수학",
        address: "경기도 시흥시 은행로 111, 3층",
        phone: "031-567-8901",
        rating: 4.5,
        reviewCount: 66,
        image: "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=600&q=80",
        description: "사고력 수학 전문! 개념부터 심화까지 탄탄하게 다집니다.",
        programs: [
            { name: "2학기 선행 특강반", duration: "4주", time: "월,수,금 오후 3:00 - 5:00", price: "280,000원" },
            { name: "사고력 쑥쑥 퀴즈대회반", duration: "4주", time: "화,목 오후 2:00 - 3:30", price: "150,000원" }
        ],
        reviews: [
            { author: "학부모A", date: "2026.05.05", content: "매일 숙제가 많긴 하지만 성적은 확실히 오르네요.", rating: 4 },
            { author: "수포자탈출", date: "2026.01.12", content: "선생님이 아이 수준에 맞춰서 꼼꼼히 설명해주십니다.", rating: 5 }
        ],
        mapUrl: "https://map.kakao.com/?q=경기도+시흥시+은행로+111"
    }
];
