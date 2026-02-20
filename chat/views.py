from django.shortcuts import render, redirect

def lobby(request):
    if request.method == 'POST':
        username = request.POST['username']
        room_name = request.POST['room_name']
        request.session['username'] = username  # store in session
        return redirect('room', room_name=room_name)
    return render(request, 'chat/lobby.html')

def room(request, room_name):
    username = request.session.get('username', None)
    if not username:
        return redirect('lobby')  # force them back if no username
    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'username': username,
    })
# Create your views here.
