# 🎂 FynCakes - Premium Handcrafted Cakes Website

A modern, customer-attracting website for FynCakes bakery in Kampala, Uganda. Built with Flask, MongoDB, and enhanced with dynamic features to maximize customer engagement and conversions.

## ✨ Features

### 🏠 **Enhanced Homepage**
- **Dynamic Statistics Counter** - Animated counters showing business metrics
- **Featured Cakes Section** - Showcases latest products with hover effects
- **Customer Testimonials** - 5-star reviews with real customer feedback
- **Newsletter Signup** - Email capture with validation and success animations
- **Professional Hero Section** - Video background with compelling CTAs

### 🛍️ **Advanced Product Showcase**
- **Smart Filtering System** - Category, price range, and sorting options
- **Quick Actions** - Hover overlays with quick view and add-to-cart buttons
- **Enhanced Product Cards** - Ratings, categories, and truncated descriptions
- **Loading States** - Professional spinners and smooth animations
- **Infinite Scroll** - "See More" functionality with API integration

### ⭐ **Social Proof & Trust Building**
- **Detailed Product Reviews** - Rating breakdowns and customer testimonials
- **Recent Orders Display** - Shows social proof with customer avatars
- **Star Ratings** - 4.9/5 stars throughout the site
- **Trust Indicators** - "Free delivery in Kampala" and quality guarantees

### 📱 **Mobile-First Design**
- **Responsive Layout** - Perfect experience on all devices
- **Touch-Friendly** - Optimized for mobile interactions
- **Fast Loading** - Optimized images and lazy loading
- **Progressive Enhancement** - Works on all browsers

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB (optional for development)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Fyncakes/ak.git
   cd ak
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   # Option 1: Use the startup script
   ./start.sh
   
   # Option 2: Run directly
   source venv/bin/activate
   python main.py
   ```

6. **Open your browser**
   Navigate to `http://localhost:5001`

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key-here
MONGO_URI=mongodb://localhost:27017/fyncakes
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### MongoDB Setup (Optional)
For full functionality, install and run MongoDB:

```bash
# Ubuntu/Debian
sudo apt-get install mongodb

# macOS with Homebrew
brew install mongodb-community

# Start MongoDB
sudo systemctl start mongod  # Linux
brew services start mongodb-community  # macOS
```

## 📁 Project Structure

```
ak/
├── cakes/
│   ├── static/
│   │   ├── css/           # Stylesheets
│   │   ├── js/            # JavaScript files
│   │   ├── cake_uploads/  # Product images
│   │   └── cake_slides/   # Homepage slides
│   ├── templates/         # HTML templates
│   ├── __init__.py        # Flask app factory
│   ├── models.py          # Data models
│   ├── routes.py          # Application routes
│   ├── forms.py           # WTForms
│   └── database.py        # Database configuration
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── start.sh              # Startup script
└── README.md             # This file
```

## 🎨 Design Features

### **Color Scheme**
- **Primary**: #D32F2F (Rich Red)
- **Accent**: #FFA000 (Warm Orange)
- **Dark**: #263238 (Professional Charcoal)
- **Light**: #FFFFFF (Clean White)

### **Typography**
- **Font Family**: Poppins (Google Fonts)
- **Weights**: 400, 500, 700
- **Responsive**: Scales beautifully on all devices

### **Interactive Elements**
- **Hover Effects**: Smooth transitions and animations
- **Loading States**: Professional spinners and feedback
- **Success Messages**: Toast notifications for user actions
- **Smooth Scrolling**: Enhanced user experience

## 🛠️ Development

### Running in Development Mode
```bash
source venv/bin/activate
export FLASK_ENV=development
python main.py
```

### Production Deployment
```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app

# Using the provided Procfile
gunicorn main:app
```

## 📊 Performance Optimizations

- **Lazy Loading**: Images load only when needed
- **Font Optimization**: Preloaded Google Fonts with fallbacks
- **CSS Minification**: Optimized stylesheets
- **JavaScript Optimization**: Efficient event handling
- **Database Indexing**: Optimized MongoDB queries
- **Caching**: Static file caching

## 🔒 Security Features

- **Input Validation**: WTForms validation on all inputs
- **CSRF Protection**: Built-in Flask-WTF protection
- **Password Hashing**: Secure password storage
- **File Upload Security**: Restricted file types and sizes
- **SQL Injection Prevention**: MongoDB parameterized queries

## 📱 Mobile Optimization

- **Responsive Grid**: Adapts to all screen sizes
- **Touch-Friendly**: Large buttons and touch targets
- **Fast Loading**: Optimized for mobile networks
- **Progressive Enhancement**: Works without JavaScript

## 🌟 Customer Attraction Features

1. **Professional Design** - Clean, modern interface that builds trust
2. **Social Proof** - Reviews and ratings build confidence
3. **Interactive Elements** - Engaging hover effects and animations
4. **Mobile-First** - Perfect experience on all devices
5. **Fast Performance** - Quick loading and smooth interactions
6. **Clear CTAs** - Prominent buttons and clear next steps
7. **Trust Indicators** - Quality guarantees and delivery promises

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, email fyncakes1@gmail.com or join our WhatsApp channel.

---

**Made with ❤️ for FynCakes - Where every slice is a piece of art! 🎂✨**
