import win32com.client as win32
print('Hvor er du')
eaApp = win32.gencache.EnsureDispatch('EA.App')
print('Her er jeg')