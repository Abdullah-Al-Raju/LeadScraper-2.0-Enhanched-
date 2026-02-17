# 🎉 Category-Aware LeadScraper - Setup Guide

## ✅ What's New?

Your LeadScraper now supports **Category-Based Discovery**! Instead of specific business names, you can search by business type/category.

### New Input Format:

| Category | Location | Status |
|----------|----------|--------|
| Restaurant | Dhaka, Bangladesh | |
| Dental Clinic | Chittagong, Bangladesh | |
| Coffee Shop | Austin, TX | |

The AI will:
1. Search for that type of business in that location
2. Find the actual business website
3. Extract the REAL business name, contact info, etc.
4. Use category-specific prompts (e.g., for restaurants: looks for chef names, cuisine, hours)

---

## 🚀 How to Use

### Step 1: Update Your Google Sheet

**Option A: Start Fresh (Recommended)**
1. Open your Google Sheet
2. The headers will auto-update to: `Category | Location | Status`
3. Add your categories:

| Category | Location | Status |
|----------|----------|--------|
| Restaurant | Dhanmondi, Dhaka | |
| Pharmacy | Chittagong | |
| Dental Clinic | Sylhet | |
| Coffee Shop | Austin, TX | |

**Option B: Keep Old Format**
- The system still supports `Business Name | City/Location | Status`
- Both formats work!

### Step 2: Run LeadScraper

```bash
cd d:\Scrapper
python main.py
```

### Step 3: Check Results

The AI will extract the **real business name** from the website, not just use your category!

**Example:**
- Input: `Restaurant | Dhaka, Bangladesh`
- Search finds: A restaurant website in Dhaka
- AI extracts: `Kacchi Bhai Restaurant` (the actual name from the website)
- Output: Full contact info for Kacchi Bhai

---

## 🧠  Category-Aware AI Features

The AI now adapts its extraction based on business type:

### Restaurant/Food Service
- Looks for: menu, cuisine type, chef/owner, business hours, delivery info

### Medical/Dental
- Looks for: doctor/dentist names, specialties, office hours, appointment numbers

### Auto Repair
- Looks for: services offered, emergency numbers, owner/manager names

### Retail/Shops
- Looks for: product categories, store hours, order contacts

### Professional Services (Law, Accounting, etc.)
- Looks for: professional names, specializations, consultation contacts

---

## 📝 Example Inputs for Bangladesh

```
Category              | Location                    | Status
Restaurant            | Gulshan, Dhaka              |
Chinese Restaurant    | Dhanmondi, Dhaka            |
Dental Clinic         | Agrabad, Chittagong         |
Pharmacy              | Sylhet                      |
Electronics Shop      | Khulna, Bangladesh          |
Coffee Shop           | Banani, Dhaka               |
Auto Repair           | Chittagong                  |
Medical Clinic        | Rangpur                     |
Bakery                | Dhaka                       |
```

---

## 💡 Pro Tips

1. **Be Specific**: "Chinese Restaurant" is better than just "Restaurant"
2. **Location Matters**: Include neighborhood/area for better results (e.g., "Gulshan, Dhaka")
3. **AI Finds Real Names**: The AI extracts the actual business name from websites
4. **Works Internationally**: Try any country!

---

## 🔧 What Changed?

**Files Modified:**
- ✅ `modules/sheets.py` - reads Category column
- ✅ `modules/extractor.py` - added category-aware AI extraction
- ✅ `main.py` - passes category to extraction
- ✅ Google Sheet headers - auto-update to Category/Location/Status

**Backwards Compatible:**
- Old format (`Business Name | City/Location | Status`) still works!
- System auto-detects which format you're using

---

## ✨ Ready to Test!

1. Open your Google Sheet
2. Clear the Status column
3. Change your inputs to categories (or keep specific names)
4. Run: `python main.py`
5. Watch the AI discover and extract business details!

**Enjoy your enhanced LeadScraper!** 🚀
